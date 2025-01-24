import random

values = ["rock", "paper", "scissors"]
game_status = True

while(game_status):
    computer_choise = random.choice(values)
    chosen_value = int(input("What do you choose? Type 0 for rock, 1 for paper or 2 for scissors"))
    try:
        value = values[chosen_value]
        if(value == computer_choise):
            print("You have equal guesses with pc ")
            continue
        elif(value == "rock" and computer_choise == "paper"):
            print("You lost ")
            break
        elif (value == "rock" and computer_choise == "scissors"):
            print("You won ")
            break
        elif (value == "paper" and computer_choise == "rock"):
            print("You won ")
            break
        elif (value == "paper" and computer_choise == "scissors"):
            print("You lost ")
            break
        elif (value == "scissors" and computer_choise == "paper"):
            print("You won ")
            break
        elif (value == "scissors" and computer_choise == "rock"):
            print("You lost ")
            break
    except Exception:
        print("No valid input given")
