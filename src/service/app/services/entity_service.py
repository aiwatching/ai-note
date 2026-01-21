"""Entity standardization service for managing unified entities across notes."""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models.entity import Entity, note_entity_association
from ..models.note import Note


class EntityService:
    """Service for entity standardization and management."""

    # Similarity thresholds for entity matching
    EXACT_MATCH_THRESHOLD = 1.0
    ALIAS_MATCH_THRESHOLD = 0.9
    FUZZY_MATCH_THRESHOLD = 0.7

    def __init__(self, db: Session):
        """Initialize entity service."""
        self.db = db

    def process_note_entities(
        self, note: Note, entities_data: Dict, user_id: int
    ) -> List[Entity]:
        """
        Process entities from note analysis and link them to the note.

        Args:
            note: The note to process entities for
            entities_data: Entities extracted from AI analysis
            user_id: User ID

        Returns:
            List of processed Entity objects
        """
        processed_entities = []

        # Process persons
        for person_data in entities_data.get("persons", []):
            entity = self._process_person_entity(person_data, user_id, note)
            if entity:
                processed_entities.append(entity)

        # Process companies
        for company_data in entities_data.get("companies", []):
            entity = self._process_company_entity(company_data, user_id, note)
            if entity:
                processed_entities.append(entity)

        # Process projects
        for project_data in entities_data.get("projects", []):
            entity = self._process_project_entity(project_data, user_id, note)
            if entity:
                processed_entities.append(entity)

        # Process locations
        for location in entities_data.get("locations", []):
            if location:
                entity = self._find_or_create_entity(
                    user_id=user_id,
                    entity_type="location",
                    name=location,
                    note=note,
                )
                if entity:
                    processed_entities.append(entity)

        # Process technical terms
        for term in entities_data.get("technical_terms", []):
            if term:
                entity = self._find_or_create_entity(
                    user_id=user_id,
                    entity_type="term",
                    name=term,
                    note=note,
                )
                if entity:
                    processed_entities.append(entity)

        self.db.commit()
        return processed_entities

    def _process_person_entity(
        self, person_data: Dict, user_id: int, note: Note
    ) -> Optional[Entity]:
        """Process a person entity with aliases."""
        if isinstance(person_data, str):
            # Simple string format
            return self._find_or_create_entity(
                user_id=user_id,
                entity_type="person",
                name=person_data,
                note=note,
            )

        # Dict format with name, aliases, role
        name = person_data.get("name")
        if not name:
            return None

        aliases = person_data.get("aliases", [])
        role = person_data.get("role")

        entity = self._find_or_create_entity(
            user_id=user_id,
            entity_type="person",
            name=name,
            aliases=aliases,
            note=note,
            metadata={"role": role} if role else None,
        )
        return entity

    def _process_company_entity(
        self, company_data: Dict, user_id: int, note: Note
    ) -> Optional[Entity]:
        """Process a company entity with aliases."""
        if isinstance(company_data, str):
            return self._find_or_create_entity(
                user_id=user_id,
                entity_type="company",
                name=company_data,
                note=note,
            )

        name = company_data.get("name")
        if not name:
            return None

        aliases = company_data.get("aliases", [])
        company_type = company_data.get("type")

        entity = self._find_or_create_entity(
            user_id=user_id,
            entity_type="company",
            name=name,
            aliases=aliases,
            note=note,
            metadata={"type": company_type} if company_type else None,
        )
        return entity

    def _process_project_entity(
        self, project_data: Dict, user_id: int, note: Note
    ) -> Optional[Entity]:
        """Process a project entity."""
        if isinstance(project_data, str):
            return self._find_or_create_entity(
                user_id=user_id,
                entity_type="project",
                name=project_data,
                note=note,
            )

        name = project_data.get("name")
        if not name:
            return None

        status = project_data.get("status")

        entity = self._find_or_create_entity(
            user_id=user_id,
            entity_type="project",
            name=name,
            note=note,
            metadata={"status": status} if status else None,
        )
        return entity

    def _find_or_create_entity(
        self,
        user_id: int,
        entity_type: str,
        name: str,
        note: Note,
        aliases: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[Entity]:
        """
        Find existing entity or create new one.

        Performs alias matching to unify entities with different names.
        """
        if not name or not name.strip():
            return None

        name = name.strip()
        aliases = [a.strip() for a in (aliases or []) if a and a.strip()]

        # Try to find existing entity by canonical name or alias
        entity = self._find_matching_entity(user_id, entity_type, name, aliases)

        if entity:
            # Update existing entity
            self._update_entity_with_note(entity, note, aliases)
        else:
            # Create new entity
            entity = Entity(
                user_id=user_id,
                entity_type=entity_type,
                canonical_name=name,
                mention_count=1,
                first_note_id=note.id,
                last_note_id=note.id,
                first_seen_at=note.created_at,
                last_seen_at=note.created_at,
            )
            if aliases:
                entity.aliases = aliases
            if metadata:
                entity.metadata_dict = metadata

            self.db.add(entity)
            self.db.flush()

        # Link entity to note if not already linked
        self._link_entity_to_note(entity, note)

        return entity

    def _find_matching_entity(
        self,
        user_id: int,
        entity_type: str,
        name: str,
        aliases: List[str],
    ) -> Optional[Entity]:
        """Find entity that matches by name or alias."""
        # Collect all names to search
        all_names = [name.lower()] + [a.lower() for a in aliases]

        # Query existing entities of this type for this user
        entities = (
            self.db.query(Entity)
            .filter(
                Entity.user_id == user_id,
                Entity.entity_type == entity_type,
            )
            .all()
        )

        for entity in entities:
            # Check canonical name
            if entity.canonical_name.lower() in all_names:
                return entity

            # Check entity's aliases
            for entity_alias in entity.aliases:
                if entity_alias.lower() in all_names:
                    return entity

            # Check if our name matches any alias
            if name.lower() in [a.lower() for a in entity.aliases]:
                return entity

        return None

    def _update_entity_with_note(
        self, entity: Entity, note: Note, new_aliases: List[str]
    ) -> None:
        """Update entity statistics and aliases when found in a new note."""
        entity.mention_count += 1
        entity.last_note_id = note.id
        entity.last_seen_at = note.created_at

        # Add new aliases
        for alias in new_aliases:
            entity.add_alias(alias)

    def _link_entity_to_note(self, entity: Entity, note: Note) -> None:
        """Create link between entity and note if not exists."""
        # Check if link already exists
        existing = self.db.execute(
            note_entity_association.select().where(
                note_entity_association.c.note_id == note.id,
                note_entity_association.c.entity_id == entity.id,
            )
        ).first()

        if not existing:
            self.db.execute(
                note_entity_association.insert().values(
                    note_id=note.id,
                    entity_id=entity.id,
                    created_at=datetime.utcnow(),
                )
            )

    def get_entities_for_note(self, note_id: int) -> List[Entity]:
        """Get all entities linked to a note."""
        return (
            self.db.query(Entity)
            .join(note_entity_association)
            .filter(note_entity_association.c.note_id == note_id)
            .all()
        )

    def get_notes_for_entity(self, entity_id: int) -> List[Note]:
        """Get all notes linked to an entity."""
        return (
            self.db.query(Note)
            .join(note_entity_association)
            .filter(note_entity_association.c.entity_id == entity_id)
            .all()
        )

    def get_user_entities(
        self,
        user_id: int,
        entity_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Entity]:
        """Get entities for a user, optionally filtered by type."""
        query = self.db.query(Entity).filter(Entity.user_id == user_id)

        if entity_type:
            query = query.filter(Entity.entity_type == entity_type)

        return query.order_by(Entity.mention_count.desc()).limit(limit).all()

    def merge_entities(
        self, primary_id: int, secondary_id: int, user_id: int
    ) -> Optional[Entity]:
        """
        Merge two entities into one.

        The secondary entity's notes and aliases are transferred to primary,
        then secondary is deleted.
        """
        primary = (
            self.db.query(Entity)
            .filter(Entity.id == primary_id, Entity.user_id == user_id)
            .first()
        )
        secondary = (
            self.db.query(Entity)
            .filter(Entity.id == secondary_id, Entity.user_id == user_id)
            .first()
        )

        if not primary or not secondary:
            return None

        if primary.entity_type != secondary.entity_type:
            logger.warning("Cannot merge entities of different types")
            return None

        # Add secondary's name as alias to primary
        primary.add_alias(secondary.canonical_name)

        # Add secondary's aliases to primary
        for alias in secondary.aliases:
            primary.add_alias(alias)

        # Update mention count
        primary.mention_count += secondary.mention_count

        # Update timestamps if needed
        if secondary.first_seen_at and (
            not primary.first_seen_at or secondary.first_seen_at < primary.first_seen_at
        ):
            primary.first_seen_at = secondary.first_seen_at
            primary.first_note_id = secondary.first_note_id

        if secondary.last_seen_at and (
            not primary.last_seen_at or secondary.last_seen_at > primary.last_seen_at
        ):
            primary.last_seen_at = secondary.last_seen_at
            primary.last_note_id = secondary.last_note_id

        # Transfer note associations
        self.db.execute(
            note_entity_association.update()
            .where(note_entity_association.c.entity_id == secondary_id)
            .values(entity_id=primary_id)
        )

        # Delete secondary entity
        self.db.delete(secondary)
        self.db.commit()

        return primary

    def get_shared_entities(self, note1: Note, note2: Note) -> List[Entity]:
        """Get entities shared between two notes."""
        entities1 = set(e.id for e in self.get_entities_for_note(note1.id))
        entities2 = set(e.id for e in self.get_entities_for_note(note2.id))

        shared_ids = entities1 & entities2
        if not shared_ids:
            return []

        return self.db.query(Entity).filter(Entity.id.in_(shared_ids)).all()

    def calculate_entity_overlap_score(self, note1: Note, note2: Note) -> float:
        """
        Calculate entity overlap score between two notes.

        Uses Jaccard similarity: intersection / union
        """
        entities1 = set(e.id for e in self.get_entities_for_note(note1.id))
        entities2 = set(e.id for e in self.get_entities_for_note(note2.id))

        if not entities1 and not entities2:
            return 0.0

        intersection = len(entities1 & entities2)
        union = len(entities1 | entities2)

        if union == 0:
            return 0.0

        return intersection / union
