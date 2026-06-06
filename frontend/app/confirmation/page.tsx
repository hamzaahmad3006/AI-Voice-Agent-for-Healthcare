'use client';

import Link from 'next/link';

export default function ConfirmationPage(): JSX.Element {
  return (
    <>
      {/* Top Nav */}
      <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-margin-mobile md:px-margin-desktop h-16 bg-surface/70 backdrop-blur-xl shadow-sm">
        <div className="flex items-center gap-xs">
          <span className="material-symbols-outlined text-primary text-3xl fill-icon">health_metrics</span>
          <span className="font-headline-md text-headline-md font-bold text-primary">VocalHealth AI</span>
        </div>
        <div className="flex items-center gap-md">
          <button className="material-symbols-outlined text-on-surface-variant hover:text-primary transition-colors duration-300 active:scale-95">
            account_circle
          </button>
          <button className="material-symbols-outlined text-on-surface-variant hover:text-primary transition-colors duration-300 active:scale-95">
            settings
          </button>
        </div>
      </header>

      {/* Main */}
      <main className="flex-grow pt-24 pb-12 px-margin-mobile flex items-center justify-center relative overflow-hidden">
        {/* Atmospheric blobs */}
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-1/2 -right-24 w-64 h-64 bg-secondary/5 rounded-full blur-3xl pointer-events-none" />

        {/* Confirmation card */}
        <div className="w-full max-w-xl animate-fade-up">
          <div className="glass-card rounded-xl p-md md:p-lg flex flex-col items-center text-center">

            {/* Success icon */}
            <div className="w-20 h-20 md:w-24 md:h-24 bg-secondary-container rounded-full flex items-center justify-center mb-md success-glow">
              <span
                className="material-symbols-outlined text-on-secondary-container text-5xl md:text-6xl font-bold"
                style={{ fontVariationSettings: "'wght' 700" }}
              >
                check
              </span>
            </div>

            <h1 className="font-headline-lg-mobile md:font-headline-lg text-headline-lg-mobile md:text-headline-lg text-on-surface mb-xs">
              Appointment Confirmed
            </h1>
            <p className="font-body-md text-body-md text-on-surface-variant mb-lg">
              Your healthcare journey is our priority. We&apos;ve sent a confirmation email with all the details.
            </p>

            {/* Details card */}
            <div className="w-full bg-surface-container-low rounded-lg p-md md:p-gutter mb-lg text-left border-l-4 border-secondary">
              <div className="grid grid-cols-1 gap-md">

                {/* Doctor */}
                <div className="flex items-start gap-md">
                  <span className="material-symbols-outlined text-primary mt-1">person</span>
                  <div>
                    <p className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider">Doctor</p>
                    <p className="font-headline-md text-headline-md text-on-surface">Dr. Sarah Mitchell</p>
                    <p className="font-caption text-caption text-secondary">Cardiologist</p>
                  </div>
                </div>

                <div className="h-px bg-outline-variant/30 w-full" />

                {/* Date + Time */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
                  <div className="flex items-start gap-md">
                    <span className="material-symbols-outlined text-primary mt-1">calendar_today</span>
                    <div>
                      <p className="font-label-caps text-label-caps text-on-surface-variant uppercase">Date</p>
                      <p className="font-body-lg text-body-lg text-on-surface">Tuesday, October 24</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-md">
                    <span className="material-symbols-outlined text-primary mt-1">schedule</span>
                    <div>
                      <p className="font-label-caps text-label-caps text-on-surface-variant uppercase">Time</p>
                      <p className="font-body-lg text-body-lg text-on-surface">10:30 AM</p>
                    </div>
                  </div>
                </div>

                <div className="h-px bg-outline-variant/30 w-full" />

                {/* Location */}
                <div className="flex items-start gap-md">
                  <span className="material-symbols-outlined text-primary mt-1">location_on</span>
                  <div className="flex-grow">
                    <p className="font-label-caps text-label-caps text-on-surface-variant uppercase">Location</p>
                    <p className="font-body-lg text-body-lg text-on-surface">Saint Jude Medical Center</p>
                    <div className="mt-sm rounded-lg overflow-hidden h-32 w-full relative">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        className="w-full h-full object-cover grayscale-[20%]"
                        alt="Saint Jude Medical Center"
                        src="https://lh3.googleusercontent.com/aida-public/AB6AXuDDg4fS8ihBuOtRLZhY0lg2wq1uZnO62cU76IO-q8T7egrCiZPX2ZSU0DgiYdO0bLg8OPwfhiyoraD9do-ChjAwH1G4H7lVIiXdqpw2X9XRHsTFkeM3lMUr6cGNB58mmzAjr1d6QPmYddkUiuhb8KZUqiAW94C0xFXsZrXiyKwogtnCn9ytkeoNy9HczH4qmpm1SzbsmTk9WsG3oBOAfI0zds4Wj2HU_wo_iLntXF-FFXLUy9BFjetJ-zuN-wfURaVquVroD9b5WEul"
                      />
                      <div className="absolute inset-0 bg-primary/10" />
                    </div>
                  </div>
                </div>

                <div className="h-px bg-outline-variant/30 w-full" />

                {/* Insurance */}
                <div className="flex items-center justify-between bg-secondary/5 p-sm rounded-lg">
                  <div className="flex items-center gap-md">
                    <span className="material-symbols-outlined text-secondary">verified_user</span>
                    <p className="font-body-md text-body-md text-on-surface">Insurance Status</p>
                  </div>
                  <span className="bg-secondary text-on-secondary px-sm py-xs rounded-full font-label-caps text-label-caps">
                    Verified
                  </span>
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex flex-col md:flex-row gap-md w-full">
              <button className="flex-1 border-2 border-outline hover:bg-surface-variant transition-all duration-300 py-md rounded-lg font-body-md font-bold text-on-surface flex items-center justify-center gap-sm active:scale-95">
                <span className="material-symbols-outlined">download</span>
                Download Receipt
              </button>
              <button className="flex-1 bg-primary text-on-primary hover:bg-primary/90 transition-all duration-300 py-md rounded-lg font-body-md font-bold flex items-center justify-center gap-sm active:scale-95 shadow-lg shadow-primary/20">
                <span className="material-symbols-outlined">calendar_add_on</span>
                Add to Calendar
              </button>
            </div>

            <Link
              href="/"
              className="mt-lg font-caption text-caption text-on-surface-variant hover:text-primary transition-colors underline decoration-dotted"
            >
              Need to reschedule or cancel?
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full py-md px-margin-mobile md:px-margin-desktop flex flex-col md:flex-row justify-between items-center gap-sm bg-surface-container border-t border-outline-variant">
        <div className="flex flex-col items-center md:items-start gap-xs">
          <span className="font-label-caps text-label-caps text-on-surface-variant">VocalHealth AI</span>
          <p className="font-caption text-caption text-secondary">© 2024 VocalHealth AI. HIPAA Compliant &amp; Secure.</p>
        </div>
        <div className="flex gap-md flex-wrap justify-center">
          {['Privacy Policy', 'Terms of Service', 'Security Compliance', 'Support'].map((item) => (
            <a key={item} className="font-caption text-caption text-on-surface-variant hover:text-primary underline transition-all duration-300" href="#">
              {item}
            </a>
          ))}
        </div>
      </footer>
    </>
  );
}
