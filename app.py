from dotenv import load_dotenv
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
import asyncio
from openai import AsyncOpenAI

# import os
# import requests
# from google.cloud import translate_v2 as translate, speech, storage
# import azure.cognitiveservices.speech as speechsdk

app = Flask(__name__)

load_dotenv()

conversation_history = []

# Map Twilio's language codes to the corresponding prompt
language_mapping = {
    "1": { "code": "en-US", "initial_prompt": "Starting the interactive session... What would you like to talk about today?" },
    "2": { "code": "es-ES", "initial_prompt": "Iniciando la sesión interactiva... ¿De qué le gustaría hablar hoy?" },
    "3": { "code": "fr-FR", "initial_prompt": "Démarrage de la session interactive... De quoi aimeriez-vous parler aujourd'hui?" }
}

@app.route("/gather", methods=["GET", "POST"])
def gather():
    response = VoiceResponse()
    gather = Gather(numDigits=1, action="/voice")
    gather.say("Welcome to the Language Learning Companion. For English, press 1.")
    gather.say("Para español, presione 2.", language="es-ES")
    gather.say("Pour le français, appuyez sur 3.",language="fr-FR")
    response.append(gather)

    # If the user doesn't select an option, redirect them into a loop
    response.redirect("/gather")

    return str(response)

@app.route("/voice", methods=["GET", "POST"])
def voice():
    response = VoiceResponse()

    if "Digits" in request.values:
        choice = request.values["Digits"]
        if choice in language_mapping:
            language = language_mapping.get(choice, {}).get("code")
            prompt = language_mapping.get(choice, {}).get("initial_prompt")

            gather = gather_user_speech(language)
            gather.say(prompt, language=language)

            while len(conversation_history) > 20:
                conversation_history.pop(2)

            conversation_history.extend((
                {
                    "role": "system",
                    "content": f"You are a helpful Language Learning Assistant. Please provide engaging but concise responses in {language}"
                },
                {
                    "role": "assistant",
                    "content": prompt
                }
            ))

            print(conversation_history)

            response.append(gather)

            return str(response)
    
    # If the user didn't respond with a valid choice, redirect them to /gather
    response.say("Sorry, I don't understand your selection. Please try again.")
    response.redirect("/gather")

    return str(response)

@app.route("/handle-speech", methods=["GET", "POST"])
def handle_speech():
    language = request.args.get("lang")
    transcript = request.values["SpeechResult"]

    print(transcript)
    
    chat_response = asyncio.run(chat_with_gpt(transcript))

    response = VoiceResponse()
    response.say(chat_response, language=language)

    gather = gather_user_speech(language)

    response.append(gather)

    return str(response)

def gather_user_speech(language):
    gather = Gather(
        input="speech",
        language=language,
        speech_model="experimental_conversations",
        action=f"/handle-speech?lang={language}"
    )

    return gather

async def chat_with_gpt(user_input):
    client = AsyncOpenAI()

    chat_completion = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            *conversation_history,
            {
                "role": "user",
                "content": user_input
            }
        ]
    )

    ai_response = chat_completion.choices[0].message.content

    print(ai_response)

    conversation_history.append({
        "role": "assistant",
        "content": ai_response
    })

    return ai_response
    


if __name__ == "__main__":
    app.run(debug=True)






# account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
# auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

# print(account_sid, auth_token)

# @app.route("/call-waiting", methods=["GET", "POST"])
# def call_waiting():
#     response = VoiceResponse()
#     response.say("Please wait while we process your recording...")
#     response.play("https://demo.twilio.com/docs/classic.mp3")

#     return str(response)

# @app.route("/handle-recording", methods=["GET", "POST"])
# def handle_recording():
#     choice = request.args.get("choice")
#     language = request.args.get("lang")
#     recording_url = request.values["RecordingUrl"]
#     print(recording_url, language, choice)

#     recognition = transcribe_audio(recording_url, language)
#     transcript = recognition["transcript"]
#     print(f"Transcript: {transcript}")

#     chat_response = asyncio.run(chat_with_gpt(transcript, language, choice))

#     response = VoiceResponse()
#     # response.record(max_length=30, action=f"/handle-recording?lang={language}")
#     feedback = provide_feedback(recognition)
#     response.say(f"Here is your feecback so far... {feedback}")
#     response.say(chat_response, language=language)

#     return str(response)

# def translate_message(target, message):
#     translate_client = translate.Client()
#     result = translate_client.translate(message, target_language=target)
#     return result["translatedText"]

# def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
#     storage_client = storage.Client()
#     bucket = storage_client.bucket(bucket_name)
#     blob = bucket.blob(destination_blob_name)
#     blob.upload_from_filename(source_file_name)

#     return f"gs://{bucket_name}/{destination_blob_name}"

# def transcribe_audio(recording_url, language_code):
#     client = speech.SpeechClient()

#     res = requests.get(recording_url, auth=(account_sid, auth_token))

#     if res.status_code == 200:
#         print(res.status_code)
#         with open("recording.wav", "wb") as f:
#             f.write(res.content)
#             upload_to_gcs("lang-recordings", "recording.wav", "recordings/recording.wav")
#     else:
#         print("Failed to download recording")

#     print("file_record")
#     audio = speech.RecognitionAudio(content="recording.wav")

#     config = speech.RecognitionConfig(
#         language_code=language_code
#     )

#     print("config")

#     response = client.recognize(config=config, audio=audio)

#     print("response")

#     for result in response.results:
#         transcript += result.alternatives[0].transcript

#     return { "transcript": transcript, "results": response.results }

# def analyze_pronunciation(results):
#     feedback = []

#     for result in results:
#         for word_info in result.alternatives[0].words:
#             word = word_info.word
#             confidence = word_info.confidence

#             if confidence < 0.8:
#                 feedback.append(f"Check pronunciation of '{word}'")

#     print(feedback)
#     return feedback

# def analyze_fluency(results):
#     total_time = 0
#     word_count = 0

#     for result in results:
#         for word_info in result.alternatives[0].words:
#             start_time = word_info.start_time.total_seconds()
#             end_time = word_info.end_time.total_seconds()
#             total_time += (end_time - start_time)
#             word_count += 1

#     speech_rate = word_count / (total_time / 60) # words per minute

#     print(f"Speech rate: {speech_rate}")

#     if speech_rate < 100:
#         return "Try speaking a bit faster for better fluency."
#     elif speech_rate > 150:
#         return "Try slowing down a bit for clarity."
#     else:
#         return "Great fluency!"
    
# def analyze_pauses(results):
#     pauses = []
#     prev_end_time = 0

#     for result in results:
#         for word_info in result.alternatives[0].words:
#             start_time = word_info.start_time.total_seconds()
#             if start_time - prev_end_time > 1:
#                 pauses.append(start_time - prev_end_time)
#             prev_end_time = word_info.end_time.total_seconds()
    
#     if pauses:
#         print(f"Pauses: {pauses}")
#         return f"Consider reducing pauses. Longest pause was {max(pauses):.2f} seconds."
    
#     return "Good job; you kept a steady pace!"

# def provide_feedback(results):
#     pronunciation_feedback = analyze_pronunciation(results)
#     fluency_feedback = analyze_fluency(results)
#     pause_feedback = analyze_pauses(results)

#     feedback = " ".join(pronunciation_feedback) + " " + fluency_feedback + " " + pause_feedback
#     print(feedback)

#     return feedback