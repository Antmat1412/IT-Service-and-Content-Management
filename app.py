from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import random

app = Flask(__name__)
app.secret_key = "super_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hangman.db"
db = SQLAlchemy(app)

# Модели
class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(30))

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)

# Инициализация БД (перенесена в контекст приложения)
def init_db():
    with app.app_context():
        db.create_all()
        if not Word.query.first():
            words = [
                Word(text="питон", category="животные"),
                Word(text="программа", category="технологии"),
                Word(text="виселица", category="игры"),
            ]
            db.session.add_all(words)
            db.session.commit()

init_db()

# --- Маршруты ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start_game():
    # Берём случайное слово из БД (вместо random.choice(WORDS))
    word = Word.query.order_by(db.func.random()).first()
    session["word"] = word.text
    session["guessed"] = []
    session["errors"] = 0
    session["player_name"] = request.form.get("player_name", "Гость")  # Новое поле
    return redirect(url_for("game"))

@app.route("/game", methods=["GET", "POST"])
def game():
    if "word" not in session:
        return redirect(url_for("index"))
    
    word = session["word"]
    guessed = session["guessed"]
    errors = session["errors"]
    max_errors = 6

    if request.method == "POST":
        letter = request.form.get("letter", "").lower()
        if letter and letter not in guessed:
            if letter in word:
                guessed.append(letter)
            else:
                errors += 1
            session["guessed"] = guessed
            session["errors"] = errors

    # Проверка победы/поражения
    if "_" not in display_word(word, guessed):
        update_stats(session["player_name"], win=True)  # Обновляем статистику
        return render_template("result.html", win=True, word=word)
    elif errors >= max_errors:
        update_stats(session["player_name"], win=False)
        return render_template("result.html", win=False, word=word)

    return render_template("game.html", 
                         word_display=display_word(word, guessed),
                         errors=errors,
                         max_errors=max_errors)

# Обновление статистики игрока
def update_stats(player_name, win):
    player = Player.query.filter_by(name=player_name).first()
    if not player:
        player = Player(name=player_name, wins=0, losses=0)
        db.session.add(player)
    if win:
        player.wins += 1
    else:
        player.losses += 1
    db.session.commit()

# Отображение слова с пропусками (например, "п _ _ _ н")
def display_word(word, guessed):
    return " ".join([letter if letter in guessed else "_" for letter in word])

# Новый маршрут для статистики
@app.route("/stats")
def stats():
    players = Player.query.order_by(Player.wins.desc()).all()  # Сортировка по победам
    return render_template("stats.html", players=players)

if __name__ == "__main__":
    app.run(debug=True)
