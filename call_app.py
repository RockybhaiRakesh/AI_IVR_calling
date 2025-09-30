from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather, Record
import os
import logging
import datetime
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Twilio credentials
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_number = os.environ.get("TWILIO_PHONE_NUMBER")
client = Client(account_sid, auth_token)

# In-memory student data store
student_data = {}

# Local folder to save recordings
local_folder = r"C:\Users\rakes\OneDrive\Desktop\Twilio_calling\recordings"
os.makedirs(local_folder, exist_ok=True)

# -------------------------
# Outbound call
# -------------------------
@app.route("/make_call")
def make_call():
    to_number = request.args.get("to")
    if not to_number:
        return "Provide ?to=+91XXXXXXXXXX", 400

    call = client.calls.create(
        url=f"{request.url_root}voice",
        to=to_number,
        from_=twilio_number
    )
    student_data[call.sid] = {}
    logging.info(f"Call initiated: {call.sid}")
    return f"Call initiated! Call SID: {call.sid}"

# -------------------------
# Initial IVR menu
# -------------------------
@app.route("/voice", methods=['GET', 'POST'])
def voice():
    resp = VoiceResponse()
    gather = Gather(num_digits=1, action="/gather_input", method="POST", timeout=5)
    gather.say(
        "Hi! I am calling from Swarise Technology. "
        "Press 1 to start providing your admission details.", voice="alice"
    )
    resp.append(gather)
    resp.say("No input received. Goodbye!", voice="alice")
    return str(resp)

# -------------------------
# Handle key press
# -------------------------
@app.route("/gather_input", methods=['GET', 'POST'])
def gather_input():
    resp = VoiceResponse()
    digit = request.values.get("Digits")
    call_sid = request.values.get("CallSid")
    if call_sid not in student_data:
        student_data[call_sid] = {}

    if digit == "1":
        # Ask Program
        resp.say("Please say the program you are interested in after the beep.", voice="alice")
        resp.record(action="/save_response?field=program", method="POST", max_length=5, play_beep=True)
    else:
        resp.say("Invalid input. Goodbye!", voice="alice")
    return str(resp)

# -------------------------
# Save any speech recording
# -------------------------
@app.route("/save_response", methods=['GET', 'POST'])
def save_response():
    resp = VoiceResponse()
    call_sid = request.values.get("CallSid")
    field = request.args.get("field", "unknown")
    recording_sid = request.values.get("RecordingSid")

    if call_sid not in student_data:
        student_data[call_sid] = {}

    if recording_sid:
        # Download recording from Twilio
        recording = client.recordings(recording_sid).fetch()
        recording_url = f"https://api.twilio.com{recording.uri.replace('.json','')}"
        file_path = os.path.join(local_folder, f"{call_sid}_{field}.wav")

        r = requests.get(recording_url, auth=HTTPBasicAuth(account_sid, auth_token))
        with open(file_path, "wb") as f:
            f.write(r.content)

        student_data[call_sid][f"{field}_recording_local"] = file_path
        logging.info(f"Saved {field} recording locally: {file_path}")
    else:
        logging.warning(f"No recording SID for {field} in call {call_sid}")

    # Decide next question
    if field == "program":
        resp.say("Do you require hostel facilities? Please say Yes or No after the beep.", voice="alice")
        resp.record(action="/save_response?field=hostel", method="POST", max_length=3, play_beep=True)
    elif field == "hostel":
        resp.say("Do you want to apply for scholarships? Please say Yes or No after the beep.", voice="alice")
        resp.record(action="/save_response?field=scholarship", method="POST", max_length=3, play_beep=True)
    elif field == "scholarship":
        resp.say("Please say your full name after the beep.", voice="alice")
        resp.record(action="/save_response?field=name", method="POST", max_length=5, play_beep=True)
    elif field == "name":
        resp.say("Please say your age after the beep.", voice="alice")
        resp.record(action="/save_response?field=age", method="POST", max_length=5, play_beep=True)
    elif field == "age":
        student_data[call_sid]['collected_at'] = datetime.datetime.now().isoformat()
        logging.info(f"Student Data {call_sid}: {student_data[call_sid]}")
        resp.say("Thank you. Your details have been recorded. Goodbye!", voice="alice")
    else:
        resp.say("Thank you. Goodbye!", voice="alice")

    return str(resp)

# -------------------------
# Run Flask
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
