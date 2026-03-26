/**
 * Shared formatting utilities - eliminates duplication between Dashboard and Layout.
 */
export function timeAgo(dateStr, t) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return t('justNow');
  if (mins < 60) return `${mins} ${t('minutesAgo')}`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} ${t('hoursAgo')}`;
  return `${Math.floor(hours / 24)} ${t('daysAgo')}`;
}

export function formatDate(dateStr, lang = 'tr') {
  return new Date(dateStr).toLocaleString(lang === 'tr' ? 'tr-TR' : 'en-US');
}

export function getSeverity(score) {
  if (score > 85) return 'crit';
  if (score > 60) return 'warn';
  return 'ok';
}

export function getSeverityColor(severity) {
  if (severity === 'crit') return 'var(--red)';
  if (severity === 'warn') return 'var(--amber)';
  return 'var(--green)';
}
