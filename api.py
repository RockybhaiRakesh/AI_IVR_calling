import os
import json
import asyncio
import aiohttp
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

load_dotenv()

# Load AI system prompt
def load_prompt(file_name):
    path = os.path.join(os.path.dirname(__file__), 'prompts', f'{file_name}.txt')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Missing prompt file: {file_name}.txt")
        return ""

SYSTEM_MESSAGE = load_prompt('system_prompt')  # Example: "Reply in English only."

# Config
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
NGROK_URL = os.getenv('NGROK_URL')
PORT = int(os.getenv('PORT', 5000))
VOICE = "alloy"
LOG_EVENT_TYPES = [
    'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]

app = FastAPI()
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Make outgoing call
@app.post("/make-call")
async def make_call(request: Request):
    data = await request.json()
    to_number = data.get("to")
    if not to_number:
        return {"error": "Provide 'to' phone number."}

    call = twilio_client.calls.create(
        url=f"{NGROK_URL}/outgoing-call",
        to=to_number,
        from_=TWILIO_PHONE_NUMBER
    )
    return {"call_sid": call.sid}

# Twilio calls this endpoint for TwiML
@app.api_route("/outgoing-call", methods=["GET", "POST"])
async def outgoing_call(request: Request):
    resp = VoiceResponse()
    resp.say("Connecting you to the AI voice assistant. You may start talking.", voice="alice")  # English only
    connect = Connect()
    connect.stream(url=f"{NGROK_URL.replace('https', 'wss')}/media-stream")
    resp.append(connect)
    return HTMLResponse(content=str(resp), media_type="application/xml")

# WebSocket: Twilio ↔ OpenAI
@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    print("Twilio connected to WebSocket")

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(
            'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as openai_ws:

            await send_session_update(openai_ws)
            stream_sid = None

            async def receive_twilio():
                nonlocal stream_sid
                try:
                    async for msg in websocket.iter_text():
                        data = json.loads(msg)
                        if data.get('event') == 'media':
                            audio_data = {
                                "type": "input_audio_buffer.append",
                                "audio": data['media']['payload']
                            }
                            await openai_ws.send_str(json.dumps(audio_data))
                        elif data.get('event') == 'start':
                            stream_sid = data['start']['streamSid']
                            print(f"Stream started: {stream_sid}")
                except WebSocketDisconnect:
                    print("Twilio disconnected.")
                    await openai_ws.close()

            async def send_to_twilio():
                nonlocal stream_sid
                try:
                    async for msg in openai_ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            response = json.loads(msg.data)
                            if response.get('type') in LOG_EVENT_TYPES:
                                print("Event:", response.get('type'))
                            if response.get('type') == 'response.audio.delta' and response.get('delta'):
                                payload = response['delta']
                                audio_msg = {
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {"payload": payload}
                                }
                                await websocket.send_json(audio_msg)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
                except Exception as e:
                    print("Error sending to Twilio:", e)

            await asyncio.gather(receive_twilio(), send_to_twilio())

# Send session update to OpenAI
async def send_session_update(openai_ws):
    session_update = {
        "type": "session.update",
        "session": {
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        }
    }
    await openai_ws.send_str(json.dumps(session_update))
    print("Sent session update to OpenAI")

# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
