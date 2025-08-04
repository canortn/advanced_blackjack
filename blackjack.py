from flask import Flask, render_template, request, redirect, url_for, session
import random
from collections import Counter

app = Flask(__name__)
app.secret_key = 'your_secret_key'

card_faces = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
card_values = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11
}

def calculate_score(hand):
    total = sum(card_values[card] for card in hand)
    aces = hand.count("A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            num_decks = int(request.form.get("num_decks", 1))
        except (ValueError, TypeError):
            num_decks = 1

        num_decks = max(1, min(num_decks, 8))
        shoe = card_faces * 4 * num_decks
        random.shuffle(shoe)

        session.clear()
        session["shoe"] = shoe
        session["num_decks"] = num_decks
        session["balance"] = 1000

        return redirect(url_for("bet"))
    return render_template("index.html")

@app.route("/bet", methods=["GET", "POST"])
def bet():
    balance = session.get("balance", 1000)
    if request.method == "POST":
        try:
            bet_amount = int(request.form.get("bet", 0))
        except (ValueError, TypeError):
            return render_template("bet.html", error="Invalid bet amount.", balance=balance)

        if bet_amount <= 0 or bet_amount > balance:
            return render_template("bet.html", error="Invalid bet amount.", balance=balance)

        shoe = session.get("shoe", [])
        if len(shoe) < 10:
            return render_template("bet.html", error="Deck is empty. Please restart the game.", balance=balance)

        session["bet"] = bet_amount
        session["player_hand"] = [shoe.pop(), shoe.pop()]
        session["dealer_hand"] = [shoe.pop(), shoe.pop()]
        session["shoe"] = shoe

        return redirect(url_for("game"))

    return render_template("bet.html", balance=balance)

@app.route("/game", methods=["GET", "POST"])
def game():
    shoe = session.get("shoe", [])
    player_hand = session.get("player_hand", [])
    dealer_hand = session.get("dealer_hand", [])

    if request.method == "POST":
        move = request.form.get("move")

        if move == "hit" and len(shoe) > 0:
            player_hand.append(shoe.pop())
            session["player_hand"] = player_hand
            session["shoe"] = shoe

            if calculate_score(player_hand) > 21:
                return redirect(url_for("result"))

        elif move == "stand":
            while calculate_score(dealer_hand) < 17 and len(shoe) > 0:
                dealer_hand.append(shoe.pop())
            session["dealer_hand"] = dealer_hand
            session["shoe"] = shoe
            return redirect(url_for("result"))

    num_decks = session.get("num_decks", 1)
    total_card_counts = Counter(card_faces * 4 * num_decks)
    current_card_counts = Counter(shoe)

    return render_template("game.html",
        player_hand=player_hand,
        dealer_card=dealer_hand[0],
        player_total=calculate_score(player_hand),
        card_counts=current_card_counts,
        total_card_counts=total_card_counts,
    )

@app.route("/result", methods=["GET", "POST"])
def result():
    player_hand = session.get("player_hand", [])
    dealer_hand = session.get("dealer_hand", [])
    bet = session.get("bet", 0)
    balance = session.get("balance", 0)

    player_score = calculate_score(player_hand)
    dealer_score = calculate_score(dealer_hand)

    # Handle Blackjack
    if player_score == 21 and len(player_hand) == 2:
        result_msg = "Blackjack! You win with 2.5x payout!"
        balance += int(bet * 2.5)
    elif player_score > 21:
        result_msg = "You busted! Dealer wins."
        balance -= bet
    elif dealer_score > 21 or player_score > dealer_score:
        result_msg = "You win!"
        balance += bet
    elif dealer_score == player_score:
        result_msg = "Push. It's a tie!"
    else:
        result_msg = "Dealer wins!"
        balance -= bet

    session["balance"] = max(balance, 0)
    session["shoe"] = session.get("shoe", [])
    session["player_hand"] = []
    session["dealer_hand"] = []

    num_decks = session.get("num_decks", 1)
    total_card_counts = Counter(card_faces * 4 * num_decks)
    current_card_counts = Counter(session["shoe"])

    return render_template(
        "result.html",
        player_hand=player_hand,
        dealer_hand=dealer_hand,
        player_total=player_score,
        dealer_total=dealer_score,
        balance=session["balance"],
        result=result_msg,
        card_counts=current_card_counts,
        total_card_counts=total_card_counts,
    )

if __name__ == "__main__":
    app.run(debug=True, port=9993)
