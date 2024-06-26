import streamlit as st
import os
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
)
import sounddevice as sd
import scipy.io.wavfile as wavfile
load_dotenv()

def record_and_save_audio():
    sample_rate = 44100

    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    if 'recording' not in st.session_state:
        st.session_state.recording = None

    if st.button("Start/Stop Recording", key="record_button"):
        if not st.session_state.is_recording:
            st.session_state.is_recording = True
            st.session_state.recording = sd.rec(int(sample_rate * 5), samplerate=sample_rate, channels=1, dtype='int16')  # Record for 5 seconds
            st.write("Recording audio...")
        else:
            st.session_state.is_recording = False
            sd.stop()
            st.session_state.recording = st.session_state.recording.reshape(-1)
            wavfile.write('u_audio.wav', sample_rate, st.session_state.recording)
            st.write("Recording complete.")
            st.success("Audio saved as 'u_audio.wav'.")

st.title("Voice Recorder")

# Audio file upload
st.sidebar.title("Audio File Upload")
uploaded_file = st.sidebar.file_uploader("Upload an audio file", type=["wav", "mp3", "ogg"])

if uploaded_file is not None:
    # Save the uploaded file with a specific name u_audio.wav
    with open("u_audio.wav", "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success("File saved as u_audio.wav")

record_and_save_audio()

# Check which audio file to use
audio_file_path = "u_audio.wav" if os.path.exists("u_audio.wav") else "test.wav"

API_KEY = os.getenv("DG_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Generate button
if st.button("Generate"):
    try:
        # Create a Deepgram client using the API key
        deepgram = DeepgramClient(API_KEY)

        with open(audio_file_path, "rb") as file:
            buffer_data = file.read()

        payload: FileSource = {
            "buffer": buffer_data,
        }

        # Configure Deepgram options for audio analysis
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
        )

        # Call the transcribe_file method with the text payload and options
        response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)

        # Print the response
        print(response)
        transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
        
        st.title("Audio transcript")
        st.write(transcript)
        
        st.divider() 

        # st.title("SOAP note")
        # OpenAI integration for generating SOAP notes
        model = ChatOpenAI(model="gpt-3.5-turbo")

        prompt = ChatPromptTemplate.from_template("""You are an expert medical assistant trained to generate detailed SOAP notes based on patient information. Your task is to create a complete SOAP note that includes the following sections:

        "Hear are the patient's data = {topic}
        you also need to figer out SOAP from the data."
        
        Subjective:
        - Summarize the patient's chief complaint, history of present illness, and any relevant past medical history, social history, or review of systems.

        Objective: 
        - Provide a summary of any relevant physical exam findings, vital signs, laboratory results, or other objective data collected during the patient encounter.

        Assessment:
        - Provide your assessment of the patient's condition, including any diagnoses or differential diagnoses.

        Plan:
        - Recommend an appropriate treatment plan, including any medications, therapies, referrals, or follow-up instructions.

        Use the following information about the patient to generate the SOAP note:

        Patient name: [Patient Name]
        Age: [Patient Age]
        Chief complaint: [Chief Complaint]
        History of present illness: [History of Present Illness]
        Past medical history: [Past Medical History]
        Social history: [Social History] 
        Review of systems: [Review of Systems]
        Physical exam findings: [Physical Exam Findings]
        Vital signs: [Vital Signs]
        Laboratory results: [Laboratory Results]

        Respond with the complete SOAP note in the following format:

        Subjective:
        [Subjective summary]

        Objective: 
        [Objective summary]

        Assessment:
        [Assessment summary]  

        Plan:
        [Plan summary] """)

        output_parser = StrOutputParser()

        chain = prompt | model | output_parser
        st.title("SOAP note")
        st.write(chain.invoke({"topic": transcript}))
        
    except Exception as e:
        st.write(f"Exception: {e}")

