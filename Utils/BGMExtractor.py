from flask import Flask, request, jsonify, send_file, render_template_string, url_for
from spleeter.separator import Separator
import os


app = Flask(__name__)
separator = Separator('spleeter:2stems')


@app.route('/')
def index():
    return render_template_string('''
        <!doctype html>
        <title>Spleeter Audio Separator</title>
        <h1>Upload an audio file to separate accompaniment</h1>
        <form method=post enctype=multipart/form-data action="/separate">
          <input type=file name=audio_file>
          <input type=submit value=Upload>
        </form>
        <audio id="audioPlayer" controls style="display:none;">
          Your browser does not support the audio element.
        </audio>
        <script>
          function playAudio(url) {
            const audioPlayer = document.getElementById('audioPlayer');
            audioPlayer.src = url;
            audioPlayer.style.display = 'block';
            audioPlayer.play();
          }
        </script>
    ''')


@app.route('/separate', methods=['POST'])
def separate_audio():
    if 'audio_file' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio_file']
    output_dir = 'output'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, audio_file.filename)
    audio_file.save(file_path)

    try:
        separator.separate_to_file(file_path, output_dir)

        # Construct the path to the accompaniment file
        base_name = os.path.splitext(audio_file.filename)[0]
        accompaniment_path = os.path.join(output_dir, base_name, 'accompaniment.wav')

        if os.path.exists(accompaniment_path):
            accompaniment_url = url_for('serve_audio', filename=f"{base_name}/accompaniment.wav")
            return render_template_string(f'''
                <!doctype html>
                <title>Accompaniment Playback</title>
                <h1>Accompaniment File Ready</h1>
                <audio controls autoplay>
                  <source src="{accompaniment_url}" type="audio/wav">
                  Your browser does not support the audio element.
                </audio>
                <br><br>
                <a href="{accompaniment_url}" download>Download Accompaniment</a>
            ''')
        else:
            return jsonify({"error": "Accompaniment file not found"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/output/<path:filename>')
def serve_audio(filename):
    return send_file(os.path.join('output', filename))


if __name__ == "__main__":
    app.run(debug=True)
