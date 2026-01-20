import { format, formatDistanceToNow, parseISO, isToday, isYesterday, isThisWeek } from 'date-fns';
import { zhCN } from 'date-fns/locale';

export function formatDate(dateString: string): string {
  const date = parseISO(dateString);
  return format(date, 'yyyy-MM-dd HH:mm', { locale: zhCN });
}

export function formatRelativeDate(dateString: string): string {
  const date = parseISO(dateString);

  if (isToday(date)) {
    return format(date, '今天 HH:mm');
  }

  if (isYesterday(date)) {
    return format(date, '昨天 HH:mm');
  }

  if (isThisWeek(date)) {
    return format(date, 'EEEE HH:mm', { locale: zhCN });
  }

  return format(date, 'MM-dd HH:mm');
}

export function formatTimeAgo(dateString: string): string {
  const date = parseISO(dateString);
  return formatDistanceToNow(date, { addSuffix: true, locale: zhCN });
}

export function formatSimpleDate(dateString: string | null): string {
  if (!dateString) return '';
  const date = parseISO(dateString);
  return format(date, 'yyyy-MM-dd');
}
