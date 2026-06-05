// Mirrors backend/models/patient.py

export type PatientMatchStatus = 'EXISTING_PATIENT' | 'NO_MATCH' | 'AMBIGUOUS';

export interface PatientRecord {
  patientId: string;
  fhirId: string;
  firstName: string;
  lastName: string;
  dob: string; // ISO 8601 date YYYY-MM-DD
  phone: string;
  email: string | null;
  postalCode: string | null;
  isNew: boolean;
  createdAt: string; // ISO 8601
}

export interface PatientLookupResponse {
  status: PatientMatchStatus;
  patient: PatientRecord | null;
  candidates: PatientRecord[];
}
