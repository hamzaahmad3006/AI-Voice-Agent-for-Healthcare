// Mirrors backend/models/appointment.py

export type UrgencyLevel = 'routine' | 'soon' | 'urgent';

export type AppointmentStatus = 'booked' | 'cancelled' | 'pending';

export interface SlotResult {
  slotId: string;
  start: string; // ISO 8601 datetime
  end: string;   // ISO 8601 datetime
  providerId: string;
  locationId: string;
}

export interface AppointmentResponse {
  appointmentId: string;
  patientId: string;
  providerId: string;
  locationId: string;
  slotId: string;
  visitType: string;
  reason: string;
  start: string; // ISO 8601 datetime
  end: string;   // ISO 8601 datetime
  status: AppointmentStatus;
  confirmationCode: string;
  consentRef: string;
  createdAt: string; // ISO 8601
}
