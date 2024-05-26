from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import random
import nltk
import speech_recognition as sr
from moviepy.editor import VideoFileClip

app = Flask(__name__)
app.secret_key = 'your_secret_key'

assignments = [
    "Math Homework - Chapter 5", "Science Project - Solar System Model",
    "History Essay - World War II",
    "English Literature - Read 'To Kill a Mockingbird'",
    "Computer Science - Python Project"
]


def get_video_files():
    video_files = []
    videos_dir = os.path.join(app.root_path, 'static', 'videos')
    for filename in os.listdir(videos_dir):
        if filename.endswith('.mp4'):
            video_files.append(filename)
    return video_files


shorts = get_video_files()

quests = []
answers = {}


@app.route('/')
def home():
    return render_template('home.html', shorts=shorts)


@app.route('/assignments')
def assignments_page():
    return render_template('assignments.html', assignments=assignments)


@app.route('/shorts')
def shorts_page():
    return render_template('shorts.html', shorts=shorts)


@app.route('/quests')
def quests_page():
    return render_template('quests.html', quests=quests, enumerate=enumerate)


@app.route('/assignments/add', methods=['GET', 'POST'])
def add_assignment():
    if request.method == 'POST':
        new_assignment = request.form.get('assignment')
        if new_assignment:
            assignments.append(new_assignment)
        return redirect(url_for('assignments_page'))
    return render_template('add_assignment.html')


@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        flash('No file part')
        return redirect(request.url)
    video_file = request.files['video']
    if video_file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if video_file:
        video_filename = video_file.filename
        video_path = os.path.join(app.root_path, 'static', 'videos',
                                  video_filename)
        video_file.save(video_path)
        flash('File uploaded successfully')

        audio_path = convert_video_to_audio(video_path)

        if audio_path:
            transcription = transcribe_audio(audio_path)

            quest_with_blanks, correct_answers = create_fill_in_the_blanks(
                transcription)
            quests.append(quest_with_blanks)
            answers[len(quests) - 1] = correct_answers

            # Update the shorts list with the newly uploaded video
            global shorts
            shorts.append(video_filename)

        return redirect(url_for('home'))


def convert_video_to_audio(video_path):
    try:
        audio_path = os.path.splitext(video_path)[0] + ".wav"
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_path, codec='pcm_s16le')
        return audio_path
    except Exception as e:
        print("Error converting video to audio:", e)
        return None


def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)

    try:
        transcription = recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        transcription = "Could not understand audio"
    except sr.RequestError:
        transcription = "Could not request results"

    return transcription


def create_fill_in_the_blanks(transcription):
    tokens = nltk.word_tokenize(transcription)
    tagged_tokens = nltk.pos_tag(tokens)
    noun_tokens = [word for word, pos in tagged_tokens if pos.startswith('NN')]

    if len(noun_tokens) <= 3:
        blanks = noun_tokens
    else:
        blanks = random.sample(noun_tokens, 3)

    blanked_transcription = transcription
    correct_answers = []

    for blank in blanks:
        blanked_transcription = blanked_transcription.replace(blank, '____', 1)
        correct_answers.append(blank)

    return blanked_transcription, correct_answers


def check_answers(user_answers, correct_answers):
    match_count = 0
    for user_ans in user_answers:
        if user_ans in correct_answers:
            match_count += 1
    return match_count >= 1


@app.route('/validate_quest/<int:quest_index>', methods=['POST'])
def validate_quest(quest_index):
    user_answers = [
        request.form.get('blank1'),
        request.form.get('blank2'),
        request.form.get('blank3')
    ]
    correct_answers = answers.get(quest_index, [])

    print(f"Correct answers: {correct_answers}")
    print(user_answers, correct_answers)
    print(check_answers(user_answers, correct_answers))

    if check_answers(user_answers, correct_answers):
        quests[quest_index] = "COMPLETED +1 $NEAR!"
        print("correct")
        return jsonify({"result": "correct"})
    else:
        print("Incorrect")
        return jsonify({"result": "incorrect"})


if __name__ == '__main__':
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    app.run(debug=True)
