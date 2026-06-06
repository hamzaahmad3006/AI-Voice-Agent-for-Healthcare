import type { FSMState } from '@/types/session';

interface Props {
  state: FSMState;
}

const STATE_STYLES: Record<FSMState, string> = {
  GREETING:           'bg-blue-100 text-blue-700',
  CONSENT_DATA:       'bg-blue-100 text-blue-700',
  IDENTIFY:           'bg-violet-100 text-violet-700',
  RETRIEVE_OR_CREATE: 'bg-violet-100 text-violet-700',
  VISIT_INTAKE:       'bg-amber-100 text-amber-700',
  SLOT_SEARCH:        'bg-amber-100 text-amber-700',
  INSURANCE_CHECK:    'bg-amber-100 text-amber-700',
  CONFIRM:            'bg-cyan-100 text-cyan-700',
  BOOK:               'bg-emerald-100 text-emerald-700',
  CLOSING:            'bg-emerald-100 text-emerald-700',
  HUMAN_HANDOFF:      'bg-orange-100 text-orange-700',
  ERROR_FALLBACK:     'bg-red-100 text-red-700',
};

const STATE_LABELS: Record<FSMState, string> = {
  GREETING:           'Greeting',
  CONSENT_DATA:       'Consent',
  IDENTIFY:           'Identify',
  RETRIEVE_OR_CREATE: 'Lookup',
  VISIT_INTAKE:       'Intake',
  SLOT_SEARCH:        'Slot Search',
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
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATE_STYLES[state]}`}
    >
      {STATE_LABELS[state]}
    </span>
  );
}
