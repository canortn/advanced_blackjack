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
    shoe = session.get("shoe", [])
    player_hand = session.get("player_hand", [])
    dealer_hand = session.get("dealer_hand", [])
    bet = session.get("bet", 0)
    original_bet = session.get("original_bet", bet // 2)

    if move == "hit":
        player_hand.append(shoe.pop())
        session["player_hand"] = player_hand
        session["shoe"] = shoe

        # ✅ Check for bust after hit
        if calculate_score(player_hand) > 21:
            return redirect(url_for("stand"))

    elif move == "stand":
        # Dealer draws until score >= 17
        while calculate_score(dealer_hand) < 17:
            dealer_hand.append(shoe.pop())
        session["dealer_hand"] = dealer_hand
        session["shoe"] = shoe
        return redirect(url_for("result"))

    elif move == "double":
        if session["balance"] >= bet:
            session["doubled"] = True
            session["balance"] -= bet
            session["bet"] += bet
            session["original_bet"] = original_bet
            player_hand.append(shoe.pop())
            session["player_hand"] = player_hand
            session["shoe"] = shoe

            # ✅ Check for bust after double
            if calculate_score(player_hand) > 21:
                return redirect(url_for("stand"))

        return redirect(url_for("stand"))

    return redirect(url_for("game"))


@app.route("/stand", methods=["POST"])
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

@app.route("/stand", methods=["POST"])
def double():
    shoe = session.get("shoe", [])
    player_hand = session.get("player_hand", [])
    bet = session.get("bet", 0)
    balance = session.get("balance", 0)

    if len(player_hand) == 2 and balance >= bet:
        player_hand.append(shoe.pop())
        session["player_hand"] = player_hand
        session["shoe"] = shoe
        session["bet"] = bet * 2
        session["balance"] = balance - bet
        session["doubled"] = True
        return redirect("/stand")

    return redirect("/game")

@app.route("/result")
def result():
    player_hand = session.get("player_hand", [])
    dealer_hand = session.get("dealer_hand", [])
    bet = session.get("bet", 0)
    original_bet = session.get("original_bet", bet // 2)
    balance = session.get("balance", 0)
    doubled = session.get("doubled", False)

    player_score = calculate_score(player_hand)
    dealer_score = calculate_score(dealer_hand)

    result_msg = ""
    
    if player_score > 21:
        result_msg = "You busted! Dealer wins."
        balance -= bet  # Lose full bet
    elif dealer_score > 21 or player_score > dealer_score:
        if len(player_hand) == 2 and player_score == 21 and not doubled:
            result_msg = "Blackjack! You win 2.5x your bet!"
            balance += int(original_bet * 2.5)
        else:
            result_msg = "You win!"
            if doubled:
                balance += 4 * original_bet  # +2x original bet
            else:
                balance += bet  # normal win
    elif dealer_score == player_score:
        result_msg = "Push. It's a tie!"
        if doubled:
            balance += 2 * original_bet  # return full double
        else:
            balance += bet  # return original
    else:
        result_msg = "Dealer wins!"
        balance -= bet  # full bet lost (double or not)

    session["balance"] = max(balance, 0)

    # Also return card counts for display
    shoe = session.get("shoe", [])
    num_decks = session.get("num_decks", 1)
    total_card_counts = Counter(card_faces * 4 * num_decks)
    current_card_counts = Counter(shoe)

    return render_template(
        "result.html",
        player_hand=player_hand,
        dealer_hand=dealer_hand,
        player_total=player_score,
        dealer_total=dealer_score,
        balance=session["balance"],
        result=result_msg,
        card_counts=current_card_counts,
        total_card_counts=total_card_counts
    )

@app.route("/restart")
def restart():
    return redirect("/bet")

if __name__ == "__main__":
    app.run(debug=True, port=9993)
