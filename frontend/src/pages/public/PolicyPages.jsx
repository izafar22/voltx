const CONTACT = "rushx779@gmail.com";

function PolicyShell({ eyebrow, title, intro, children }) {
  return (
    <article className="rx-policy rx-wrap">
      <header className="rx-policy-intro">
        <p className="rx-eyebrow">RushX / {eyebrow}</p>
        <h1>{title}</h1>
        <p className="rx-lead">{intro}</p>
        <p className="rx-policy-date">Last updated: 20 November 2026</p>
      </header>
      <div className="rx-policy-body">{children}</div>
    </article>
  );
}

function ContactLink() {
  return <a href={`mailto:${CONTACT}`}>{CONTACT}</a>;
}

export function PrivacyPolicy() {
  return (
    <PolicyShell
      eyebrow="Privacy"
      title="Privacy Policy"
      intro="How RushX handles information when you visit our website, sign in or use our charger-repair coordination services."
    >
      <section>
        <h2>About this policy</h2>
        <p>
          This policy explains how RushX handles information when you visit
          evchargerrepair.in, sign in, submit a charger repair request or use
          our repair coordination services.
        </p>
      </section>
      <section>
        <h2>Information you provide</h2>
        <p>
          Depending on the features you use, we handle account and contact
          details, verified mobile numbers, email and linked Google account
          information, saved pickup or delivery addresses, charger details,
          reported faults, repair photographs and information you send our
          team. Repair records may include inspection findings, estimates,
          your decisions, status history, payment amounts and references, and
          courier or tracking details.
        </p>
      </section>
      <section>
        <h2>Why we use it</h2>
        <p>
          We use this information to manage your account, verify sign-in,
          assess and coordinate repair requests, share estimates, record
          approvals and payment verification, arrange relevant repair
          logistics, provide service updates, respond to questions and protect
          the service from misuse.
        </p>
      </section>
      <section>
        <h2>Sign-in and WhatsApp updates</h2>
        <p>
          WhatsApp verification messages help you sign in or verify a mobile
          number. They do not automatically enrol a repair in lifecycle
          updates. Repair updates are optional and selected for an individual
          repair using your verified number. You can stop those updates from
          repair details and continue following progress in your account. A
          message already sent or in flight may still arrive. Stopping updates
          does not itself delete your account or repair or payment records.
        </p>
      </section>
      <section>
        <h2>Service providers and access</h2>
        <p>
          We use service providers for functions such as hosting and database
          operation, Google sign-in, WhatsApp delivery and repair logistics.
          We share relevant information only as needed to support the function
          being used, such as arranging an eligible collection or return. Our
          team accesses account and repair information through the service's
          access controls.
        </p>
      </section>
      <section>
        <h2>Cookies and website technologies</h2>
        <p>
          The service uses browser storage and session mechanisms to keep you
          signed in securely and remember settings such as your theme
          preference. The site loads fonts from Google Fonts, which means your
          browser connects to Google's font service when the page loads. RushX
          does not intentionally run website analytics or session-recording
          code on these pages. Service and infrastructure logs may still
          contain technical information needed to operate, secure and diagnose
          the service.
        </p>
      </section>
      <section>
        <h2>Retention and requests</h2>
        <p>
          We retain information needed to operate accounts and repair services
          and to address relevant support, payment, security and recordkeeping
          needs. Some verification or session records have expiry controls.
          You can ask us about access, correction or deletion of information
          associated with you. We review ownership and the records involved
          and explain any information that needs to be retained and why.
        </p>
      </section>
      <section>
        <h2>Contact and changes</h2>
        <p>
          For privacy questions or requests, contact <ContactLink />. We
          identify material updates through the page's updated date.
        </p>
      </section>
    </PolicyShell>
  );
}

export function DataDeletion() {
  return (
    <PolicyShell
      eyebrow="Data deletion"
      title="Data-deletion Instructions"
      intro="How to ask RushX to review or delete information associated with your account or repair."
    >
      <section>
        <h2>Request deletion</h2>
        <p>
          Email <ContactLink /> with the subject “RushX data-deletion request”.
          Identify the mobile number or email associated with your account
          and, if relevant, the repair request number. Describe whether you
          want an address removed, particular information reviewed, or your
          account information considered for deletion.
        </p>
        <p>
          We may ask for proportionate information to verify that the request
          belongs to you. Do not send your password, sign-in OTP, payment PIN
          or unrelated identity documents with the initial request.
        </p>
      </section>
      <section>
        <h2>What happens next</h2>
        <p>
          We review the request and the records involved, then explain what can
          be deleted or anonymised and any information that needs to remain for
          an ongoing repair, payment reconciliation, dispute, security or other
          applicable recordkeeping need.
        </p>
        <p>
          You can edit or remove eligible saved addresses from your profile.
          Whole-account deletion is currently a request to our team; this page
          does not perform deletion or change a repair or payment record by
          itself. Requests involving information processed by another service
          may also need that provider's process; we explain relevant limits
          when responding.
        </p>
      </section>
      <section>
        <h2>Stop repair updates</h2>
        <p>
          To stop optional WhatsApp repair messages, open that repair's details
          and choose “Stop WhatsApp updates”. This is separate from requesting
          deletion and does not remove service records or recall messages
          already sent.
        </p>
      </section>
    </PolicyShell>
  );
}
