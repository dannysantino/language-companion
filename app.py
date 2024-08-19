from dotenv import load_dotenv
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather

from feedback import transcribe_audio, provide_feedback

# import azure.cognitiveservices.speech as speechsdk

app = Flask(__name__)

load_dotenv()

# Map Twilio's language codes to the corresponding prompt
language_mapping = {
    "1": { "code": "en-US", "initial_prompt": "Starting the interactive session... What would you like to talk about today?" },
    "2": { "code": "es-ES", "initial_prompt": "Iniciando la sesión interactiva... ¿De qué le gustaría hablar hoy?" },
    "3": { "code": "fr-FR", "initial_prompt": "Démarrage de la session interactive... De quoi aimeriez-vous parler aujourd'hui?" }
}

@app.route("/gather", methods=["GET", "POST"])
def gather():
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/voice")
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
            response.say(prompt, language=language)
            response.record(max_length=10, action=f"/handle-recording?lang={language}&choice={choice}")

            return str(response)
    
    # If the user didn't respond with a valid choice, redirect them to /gather
    response.say("Sorry, I don't understand your selection. Please try again.")
    response.redirect("/gather")

    return str(response)

@app.route("/handle-recording", methods=["GET", "POST"])
def handle_recording():
    response = VoiceResponse()
    response.say("Please wait while your recording is being processed...")

    transcript = ""
    language = request.args.get("lang")
    recording_url = request.values["RecordingUrl"]
    filename = request.values["RecordingSid"] + ".wav"

    recognition_results = transcribe_audio(recording_url, filename, language)
    
    for result in recognition_results:
        transcript += result.alternatives[0].transcript

    # chat_response = asyncio.run(chat_with_gpt(transcript, language, choice))

    # response.record(max_length=30, action=f"/handle-recording?lang={language}")
    feedback = provide_feedback(recognition_results)
    response.say(f"Here is your feedback so far... {feedback}")

    gather = Gather(num_digits=1, action=f"/record?lang={language}")
    gather.say("Press 1 if you would like to record again. Or press 2 to hangup.")

    response.append(gather)

    return str(response)

@app.route("/record", methods=["GET", "POST"])
def record():
    response = VoiceResponse()

    if "Digits" in request.values:
        choice = request.values["Digits"]
        language = request.args.get("lang")

        if choice == "1":
            response.record(max_length=10, action=f"/handle-recording?lang={language}&choice={choice}")
            return str(response)
        else:
            response.say("Thank you for using the Language Learning Companion. Have a great day!")
            response.hangup()
            return str(response)

    return str(response)


if __name__ == "__main__":
    app.run(debug=True)



# def translate_message(target, message):
#     translate_client = translate.Client()
#     result = translate_client.translate(message, target_language=target)
#     return result["translatedText"]

# @app.route("/call-waiting", methods=["GET", "POST"])
# def call_waiting():
#     response = VoiceResponse()
#     response.say("Please wait while we process your recording...")
#     response.play("https://demo.twilio.com/docs/classic.mp3")

#     return str(response)

# async def chat_with_gpt(user_input, language, choice):
#     client = AsyncOpenAI()

#     chat_completion = await client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {
#                 "role": "system",
#                 "content": f"You are a helpful Language Learning Assistant. Please provide engaging but concise responses in {language}"
#             },
#             {
#                 "role": "assistant",
#                 "content": language_mapping.get(choice, {}).get("initial_promt")
#             },
#             {
#                 "role": "user",
#                 "content": user_input
#             }
#         ]
#     )

#     return chat_completion.choices[0].message.content