import type { FSMState } from '@/types/session';

interface Props {
  state: FSMState;
}

const STATE_STYLES: Record<FSMState, string> = {
  GREETING:           'bg-primary-fixed text-on-primary-fixed-variant',
  CONSENT_DATA:       'bg-primary-fixed text-on-primary-fixed-variant',
  IDENTIFY:           'bg-secondary-container text-on-secondary-container',
  RETRIEVE_OR_CREATE: 'bg-secondary-container text-on-secondary-container',
  VISIT_INTAKE:       'bg-tertiary-fixed text-on-tertiary-fixed-variant',
  SLOT_SEARCH:        'bg-tertiary-fixed text-on-tertiary-fixed-variant',
  INSURANCE_CHECK:    'bg-tertiary-fixed text-on-tertiary-fixed-variant',
  CONFIRM:            'bg-surface-container-high text-on-surface',
  BOOK:               'bg-secondary-container text-on-secondary-container',
  CLOSING:            'bg-secondary-container text-on-secondary-container',
  HUMAN_HANDOFF:      'bg-error-container text-on-error-container',
  ERROR_FALLBACK:     'bg-error-container text-on-error-container',
};

const STATE_LABELS: Record<FSMState, string> = {
  GREETING:           'Greeting',
  CONSENT_DATA:       'Consent',
  IDENTIFY:           'Identify',
  RETRIEVE_OR_CREATE: 'Lookup',
  VISIT_INTAKE:       'Intake',
  SLOT_SEARCH:        'Slots',
  INSURANCE_CHECK:    'Insurance',
  CONFIRM:            'Confirm',
  BOOK:               'Booking',
  CLOSING:            'Closing',
  HUMAN_HANDOFF:      'Handoff',
  ERROR_FALLBACK:     'Error',
};

export default function StateBadge({ state }: Props): JSX.Element {
  return (
    <span
      className={`inline-flex items-center rounded-full px-sm py-xs font-label-caps text-label-caps ${STATE_STYLES[state]}`}
    >
      {STATE_LABELS[state]}
    </span>
  );
}
