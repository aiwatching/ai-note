import React from 'react';
import { format, isToday, isTomorrow, isPast } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import {
  Calendar,
  Clock,
  MapPin,
  Users,
  CheckCircle2,
  XCircle,
  Loader2,
  MoreVertical,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { Schedule } from '@/types';
import { cn } from '@/utils/cn';

interface ScheduleListProps {
  schedules: Schedule[];
  onStatusChange: (id: number, status: string) => void;
  onDelete: (id: number) => void;
  isLoading?: boolean;
}

export function ScheduleList({
  schedules,
  onStatusChange,
  onDelete,
  isLoading,
}: ScheduleListProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (schedules.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <Calendar className="h-16 w-16 mb-4 opacity-30" />
        <p className="text-lg font-medium">暂无日程</p>
        <p className="text-sm mt-1">从笔记中创建日程安排</p>
      </div>
    );
  }

  // Group by date
  const grouped = groupSchedulesByDate(schedules);

  return (
    <div className="space-y-6">
      {grouped.map((group) => (
        <div key={group.label}>
          <h3 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            {group.label}
            <span className="text-xs">({group.schedules.length})</span>
          </h3>
          <div className="space-y-2">
            {group.schedules.map((schedule) => (
              <ScheduleItem
                key={schedule.id}
                schedule={schedule}
                onStatusChange={onStatusChange}
                onDelete={onDelete}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

interface GroupedSchedules {
  label: string;
  schedules: Schedule[];
}

function groupSchedulesByDate(schedules: Schedule[]): GroupedSchedules[] {
  const groups: { [key: string]: Schedule[] } = {};

  schedules.forEach((schedule) => {
    const date = new Date(schedule.start_time);
    let label: string;

    if (isToday(date)) {
      label = '今天';
    } else if (isTomorrow(date)) {
      label = '明天';
    } else if (isPast(date)) {
      label = '已过期';
    } else {
      label = format(date, 'M月d日 EEEE', { locale: zhCN });
    }

    if (!groups[label]) {
      groups[label] = [];
    }
    groups[label].push(schedule);
  });

  // Sort groups: 已过期, 今天, 明天, then by date
  const order = ['已过期', '今天', '明天'];
  const result: GroupedSchedules[] = [];

  order.forEach((label) => {
    if (groups[label]) {
      result.push({ label, schedules: groups[label] });
      delete groups[label];
    }
  });

  // Add remaining groups sorted by date
  Object.keys(groups)
    .sort((a, b) => {
      const dateA = groups[a][0]?.start_time;
      const dateB = groups[b][0]?.start_time;
      return new Date(dateA).getTime() - new Date(dateB).getTime();
    })
    .forEach((label) => {
      result.push({ label, schedules: groups[label] });
    });

  return result;
}

interface ScheduleItemProps {
  schedule: Schedule;
  onStatusChange: (id: number, status: string) => void;
  onDelete: (id: number) => void;
}

function ScheduleItem({ schedule, onStatusChange, onDelete }: ScheduleItemProps) {
  const startDate = new Date(schedule.start_time);
  const isCompleted = schedule.status === 'completed';
  const isCancelled = schedule.status === 'cancelled';
  const isOverdue = isPast(startDate) && schedule.status === 'scheduled';

  const getStatusBadge = () => {
    if (isCompleted) {
      return <Badge variant="secondary" className="bg-green-100 text-green-700">已完成</Badge>;
    }
    if (isCancelled) {
      return <Badge variant="secondary" className="bg-gray-100 text-gray-500">已取消</Badge>;
    }
    if (isOverdue) {
      return <Badge variant="destructive">已过期</Badge>;
    }
    return null;
  };

  return (
    <Card
      className={cn(
        'transition-colors',
        (isCompleted || isCancelled) && 'opacity-60'
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* Title and Status */}
            <div className="flex items-center gap-2 flex-wrap">
              <h4
                className={cn(
                  'font-medium',
                  (isCompleted || isCancelled) && 'line-through text-muted-foreground'
                )}
              >
                {schedule.title}
              </h4>
              {getStatusBadge()}
            </div>

            {/* Description */}
            {schedule.description && (
              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                {schedule.description}
              </p>
            )}

            {/* Time */}
            <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                {schedule.is_all_day ? (
                  '全天'
                ) : (
                  <>
                    {format(startDate, 'HH:mm', { locale: zhCN })}
                    {schedule.end_time && (
                      <> - {format(new Date(schedule.end_time), 'HH:mm', { locale: zhCN })}</>
                    )}
                  </>
                )}
              </span>

              {/* Location */}
              {schedule.location && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5" />
                  {schedule.location}
                </span>
              )}

              {/* Participants */}
              {schedule.participants && schedule.participants.length > 0 && (
                <span className="flex items-center gap-1">
                  <Users className="h-3.5 w-3.5" />
                  {schedule.participants.slice(0, 2).join(', ')}
                  {schedule.participants.length > 2 && ` +${schedule.participants.length - 2}`}
                </span>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1">
            {schedule.status === 'scheduled' && (
              <>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-green-600 hover:text-green-700 hover:bg-green-50"
                  onClick={() => onStatusChange(schedule.id, 'completed')}
                  title="标记完成"
                >
                  <CheckCircle2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => onStatusChange(schedule.id, 'cancelled')}
                  title="取消日程"
                >
                  <XCircle className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
