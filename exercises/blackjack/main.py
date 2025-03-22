import random

def create_deck():
    list_of_numbers = []
    for i in range(1, 5):
        for j in range(1, 14):
            list_of_numbers.append(j)
        

    return list_of_numbers

def deal(deck, user, dealer):
    for i in range(1, 4):
        if len(user) <= len(dealer):
            user.append(deck.pop())
        else:
            dealer.append(deck.pop())

def count_score(user:list, dealer:list):
    user_score = 0
    dealer_score = 0
    for i in user:
        if i > 10:
            user_score += 10
        elif i == 1:
            if user_score < 11:
                user_score += 11
            else:
                user_score += 1
        else:
            user_score += i

    for i in dealer:
        if i > 10:
            dealer_score += 10
        elif i == 1:
            if dealer_score < 11:
                dealer_score += 11
            else:
                dealer_score += 1
        else:
            dealer_score += i

    print(f"Player cards: {user}")
    print(f"Dealer cards: {dealer}")
    return user_score, dealer_score


def winner(user_score, dealer_score):
    print(f"Player cards: {user_score}")
    print(f"Dealer cards: {dealer_score}")
    if user_score == dealer_score:
        print("Draw")
    elif user_score == 21:
        print("blackjack!")
    elif dealer_score == 21:
        print("Bust")
    elif user_score > 21:
        print("Bust")
    elif dealer_score > 21:
        print("Dealer busted")
    elif user_score > dealer_score:
        print("You won!")
    else:
        print("You lost")
    


deck = create_deck()

random.shuffle(deck)

user_cards = []
dealer_cards = []

deal(deck, user_cards, dealer_cards)
print(f"Player cards: {user_cards}")
print(f"Dealer cards: {dealer_cards}")
while True:
    current = count_score(user_cards, dealer_cards)
    hit = input("Do you want to hit another card ? y / n:   ")
    if hit.lower() == "n":
        while current[1] < 17:
            dealer_cards.append(deck.pop())
            current = count_score(user_cards, dealer_cards)
        winner(current[0], current[1])
        break
    user_cards.append(deck.pop())
    current = count_score(user_cards, dealer_cards)
    print(f"Player cards: {user_cards}")
    print(f"Dealer cards: {dealer_cards}")
    if current[0] > 21:
        winner(current[0], current[1])
        break
    elif current[0] == 21:
        winner(current[0], current[1])
        break



