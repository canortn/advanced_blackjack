from flask import Flask, render_template, request, redirect, url_for, session
import random
from collections import Counter

app = Flask(__name__)
app.secret_key = 'your_secret_key'

card_faces = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
card_values = {
    "2": 2, "3": 2, "4": 2, "5": 3, "6": 3,
    "7": 1, "8": 0, "9": -1, "10": -2,
    "J": -2, "Q": -2, "K": -2, "A": -1
}
card_scores = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11
}

def calculate_score(hand):
    total = sum(card_scores[card] for card in hand)
    aces = hand.count("A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/setup", methods=["POST"])
def setup():
    num_decks = int(request.form.get("num_decks", 1))
    num_decks = max(1, min(num_decks, 8))
    shoe = card_faces * 4 * num_decks
    random.shuffle(shoe)

    session["shoe"] = shoe
    session["num_decks"] = num_decks
    session["balance"] = 10000
    return redirect("/bet")

@app.route("/bet", methods=["GET", "POST"])
def bet():
    balance = session.get("balance", 10000)
    if request.method == "POST":
        try:
            bet_amount = int(request.form.get("bet", 0))
        except (ValueError, TypeError):
            return render_template("bet.html", error="Invalid bet amount.", balance=balance)

        if bet_amount > balance or bet_amount <= 0:
            return render_template("bet.html", error="Invalid bet.", balance=balance)

        session["bet"] = bet_amount
        session["original_bet"] = bet_amount
        session["player_hand"] = [session["shoe"].pop(), session["shoe"].pop()]
        session["dealer_hand"] = [session["shoe"].pop(), session["shoe"].pop()]
        session["doubled"] = False
        return redirect("/game")

    return render_template("bet.html", balance=balance)

@app.route("/game")
def game():
    player_hand = session.get("player_hand", [])
    dealer_hand = session.get("dealer_hand", [])
    shoe = session.get("shoe", [])
    num_decks = session.get("num_decks", 1)
    bet = session.get("bet", 0)
    balance = session.get("balance", 0)

    allow_double = len(player_hand) == 2 and balance >= bet

    # This calculates total cards that existed based on decks
    total_card_counts = Counter(card_faces * 4 * num_decks)
    # This counts remaining cards left in the shoe
    current_card_counts = Counter(shoe)

    return render_template(
        "game.html",
        player_hand=player_hand,
        dealer_card=dealer_hand[0],
        player_total=calculate_score(player_hand),
        card_counts=current_card_counts,
        total_card_counts=total_card_counts,  # <-- This was missing
        allow_double=allow_double
    )


def get_hand_value(hand):
    total = 0
    aces = 0
    for card in hand:
        if card in ['J', 'Q', 'K']:
            total += 10
        elif card == 'A':
            total += 11
            aces += 1
        else:
            total += int(card)

    # Adjust Aces from 11 to 1 if busting
    while total > 21 and aces:
        total -= 10
        aces -= 1

    return total


@app.route("/action", methods=["POST"])
def action():
    move = request.form["move"]
    player_hand = session.get("player_hand", [])
    shoe = session.get("shoe", [])
    double_down = session.get("double_down", False)
    bet = session.get("bet", 1000)

    if move == "hit":
        player_hand.append(shoe.pop())
        session["player_hand"] = player_hand
        if calculate_score(player_hand) > 21:
            return redirect(url_for("result"))
        return redirect(url_for("hit"))

    elif move == "double":
        if not double_down:
            session["double_down"] = True
            #session["bet"] = bet * 2  # Double it ONCE
        #player_hand.append(shoe.pop())
        session["player_hand"] = player_hand
        return redirect(url_for("double"))

    elif move == "stand":
        return redirect(url_for("stand"))

    return redirect(url_for("game"))


@app.route("/hit", methods=["GET", "POST"])
def hit():
    shoe = session.get("shoe", [])
    player_hand = session.get("player_hand", [])

    if shoe:
        player_hand.append(shoe.pop())

    session["player_hand"] = player_hand
    session["shoe"] = shoe

    if calculate_score(player_hand) > 21:
        return redirect("/result")

    return redirect("/game")

@app.route("/stand", methods=["GET", "POST"])
def stand():
    shoe = session.get("shoe", [])
    dealer_hand = session.get("dealer_hand", [])

    while calculate_score(dealer_hand) < 17 and shoe:
        dealer_hand.append(shoe.pop())

    session["dealer_hand"] = dealer_hand
    session["shoe"] = shoe

    return redirect("/result")

@app.route("/double", methods=["GET", "POST"])
def double():
    shoe = session.get("shoe", [])
    player_hand = session.get("player_hand", [])
    bet = session.get("bet", 0)
    balance = session.get("balance", 0)

    if  balance >= bet:
        player_hand.append(shoe.pop())
        session["player_hand"] = player_hand
        session["shoe"] = shoe
        session["bet"] = bet * 2
        #session["balance"] = balance - bet * 2
        session["doubled"] = True
        print(session)
        return redirect("/stand")
        

    return redirect("/game")

@app.route("/result")
def result():
    player_hand = session.get("player_hand", [])
    dealer_hand = session.get("dealer_hand", [])
    bet = session.get("bet", 1000)
    balance = session.get("balance", 10000)

    player_total = calculate_score(player_hand)
    dealer_total = calculate_score(dealer_hand)

    # Default outcome
    outcome = ""

    if player_total > 21:
        outcome = "You busted! You lose."
        balance -= bet

    elif dealer_total > 21:
        outcome = "Dealer busted! You win!"
        balance += bet

    elif player_total > dealer_total:
        outcome = "You win!"
        balance += bet

    elif player_total < dealer_total:
        outcome = "You lose."
        balance -= bet

    else:
        outcome = "Push! It's a tie."

    # Save updated balance
    session["balance"] = balance

    return render_template(
        "result.html",
        outcome=outcome,
        player_hand=player_hand,
        dealer_hand=dealer_hand,
        player_total=player_total,
        dealer_total=dealer_total,
        balance=balance
    )

@app.route("/restart")
def restart():
    return redirect("/bet")

if __name__ == "__main__":
    app.run(debug=True, port=9993)
