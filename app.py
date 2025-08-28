import os
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from data_processor import DataProcessor

# -----------------------------
# Flask App Setup
# -----------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "healthcare-finder-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# -----------------------------
# Data Layer
# -----------------------------
data_processor = DataProcessor()

# -----------------------------
# SMTP / Email Config
# -----------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # SSL
SMTP_USER = "netsenseservices@gmail.com"           # Your Gmail
SMTP_PASS = "ukhr zqxo gihn yyak"              # Gmail App Password
ADMIN_EMAIL = "netsenseservices@gmail.com"         # Admin fallback


def send_email(to_email: str, subject: str, body: str, reply_to: str | None = None, bcc: str | None = None):
    """Send email via Gmail SMTP with SSL."""
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to

    recipients = [to_email]
    if bcc and bcc not in recipients:
        recipients.append(bcc)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, recipients, msg.as_string())


# -----------------------------
# Routes
# -----------------------------
@app.route('/')
def index():
    """Main page with the healthcare provider finder interface."""
    return render_template('index.html')


@app.route('/search_providers', methods=['POST'])
def search_providers():
    try:
        user_lat = float(request.form.get('latitude'))
        user_lon = float(request.form.get('longitude'))
        provider_type = (request.form.get('provider_type') or 'Hospital').lower()

        providers = data_processor.find_nearby_providers(
            user_lat, user_lon, provider_type, radius_km=15
        )

        sorted_providers = data_processor.sort_providers_by_priority(providers)

        return jsonify({
            'success': True,
            'providers': sorted_providers,
            'count': len(sorted_providers)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/get_provider_types')
def get_provider_types():
    types = data_processor.get_provider_types()
    return jsonify({'success': True, 'types': types})


# -----------------------------
# Feedback: send to provider or admin
# -----------------------------
@app.route('/send_feedback', methods=['POST'])
def send_feedback():
    try:
        # ✅ Parse JSON instead of form
        data = request.get_json(silent=True) or {}
        provider_email = (data.get('provider') or "").strip()
        message = (data.get('feedback') or "").strip()
        member_name = (data.get('member_name') or "Anonymous").strip()
        member_email = (data.get('member_email') or "").strip()

        if not message:
            return jsonify({'success': False, 'error': 'Message is required.'}), 400

        # Always fallback to admin if provider email missing
        if not provider_email:
            provider_email = ADMIN_EMAIL

        # Compose email body
        body_lines = [
            f"New feedback from: {member_name}",
        ]
        if member_email:
            body_lines.append(f"Member email: {member_email}")
        body_lines.append("")
        body_lines.append("Message:")
        body_lines.append(message)
        body = "\n".join(body_lines)

        subject = f"Healthcare Finder: Feedback from {member_name}"

        # Send email
        send_email(
            to_email=provider_email,
            subject=subject,
            body=body,
            reply_to=member_email if member_email else None,
            bcc=ADMIN_EMAIL if provider_email != ADMIN_EMAIL else None
        )

        return jsonify({'success': True, 'message': 'Feedback sent successfully!'})
    except Exception as e:
        print(f"❌ Error sending feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# -----------------------------
# Main
# -----------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
