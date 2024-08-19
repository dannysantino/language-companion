import os
import requests
from google.cloud import speech, storage

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

def upload_to_gcs(bucket_name, source_file_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    destination_blob_name = "recordings/" + source_file_name
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)

    return f"gs://{bucket_name}/{destination_blob_name}"

def transcribe_audio(recording_url, filename, language_code):
    client = speech.SpeechClient()

    try:
        res = requests.get(recording_url, auth=(account_sid, auth_token))
            
    except:
        print("Failed to download recording.")
        
    else:
        with open(filename, "wb") as audio_file:
            audio_file.write(res.content)
            gcs_uri = upload_to_gcs("lang-recordings", filename)

    audio = speech.RecognitionAudio(uri=gcs_uri)

    config = speech.RecognitionConfig(
        language_code=language_code,
        enable_word_time_offsets=True,
        enable_word_confidence=True
    )

    response = client.recognize(config=config, audio=audio)

    print("recognition response received")

    return response.results

def analyze_pronunciation(results):
    feedback = ""
    low_confidence_words = []

    for result in results:
        for word_info in result.alternatives[0].words:
            word = word_info.word
            confidence = word_info.confidence

            if confidence < 0.8:
                low_confidence_words.append(word)
                
    if len(low_confidence_words) == 0:
        feedback = "You have high pronunciation accuracy!"
    else:
        feedback = "Check your pronunciation of the following words: "
        for word in low_confidence_words:
            feedback = feedback + word + ". "
    
    return feedback

def analyze_fluency(results):
    total_time = 0
    word_count = 0

    for result in results:
        for word_info in result.alternatives[0].words:
            start_time = word_info.start_time.total_seconds()
            end_time = word_info.end_time.total_seconds()
            total_time += (end_time - start_time)
            word_count += 1

    speech_rate = word_count / (total_time / 60) # words per minute

    if speech_rate < 100:
        return "You should try speaking a bit faster for better fluency."
    elif speech_rate > 150:
        return "You should try slowing down a bit for clarity."
    else:
        return "Great fluency!"
    
def analyze_pauses(results):
    pauses = []
    prev_end_time = 0

    for result in results:
        for word_info in result.alternatives[0].words:
            start_time = word_info.start_time.total_seconds()
            if start_time - prev_end_time > 1:
                pauses.append(start_time - prev_end_time)
            prev_end_time = word_info.end_time.total_seconds()
    
    if pauses:
        return f"Consider reducing pauses. Longest pause was {max(pauses):.2f} seconds."
    
    return "You did well in keeping a steady pace! Good job!"

def provide_feedback(results):
    pronunciation_feedback = analyze_pronunciation(results)
    fluency_feedback = analyze_fluency(results)
    pause_feedback = analyze_pauses(results)

    feedback = pronunciation_feedback + " " + fluency_feedback + " " + pause_feedback
    print(feedback)

    return feedback