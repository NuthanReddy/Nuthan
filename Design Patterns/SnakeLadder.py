
class Snake:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __repr__(self):
        return f"Snake({self.start}, {self.end})"


class Ladder:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __repr__(self):
        return f"Ladder({self.start}, {self.end})"


class Board:
    def __init__(self, size):
        self.size = size
        self.snakes = []
        self.ladders = []

    def add_snake(self, snake):
        self.snakes.append(snake)

    def add_ladder(self, ladder):
        self.ladders.append(ladder)

    def __repr__(self):
        return f"Board(size={self.size}, snakes={self.snakes}, ladders={self.ladders})"


class Player:
    def __init__(self, name):
        self.name = name
        self.position = 0

    def move(self, steps):
        if self.position <= 100:
            self.position += steps

    def __repr__(self):
        return f"Player(name={self.name}, position={self.position})"


class Game:
    def __init__(self, board):
        self.board = board
        self.players = []

    def add_player(self, player):
        self.players.append(player)

    def play_turn(self, player, steps):
        player.move(steps)
        for snake in self.board.snakes:
            if player.position == snake.start:
                player.position = snake.end
                print(f"{player.name} encountered a snake! Moved to {player.position}")
        for ladder in self.board.ladders:
            if player.position == ladder.start:
                player.position = ladder.end
                print(f"{player.name} climbed a ladder! Moved to {player.position}")

    def is_winner(self, player):
        return player.position == 100

    def play_game(self):
        while True:
            for player in self.players:
                steps = self.roll_dice()
                print(f"{player.name} rolled a {steps}")
                self.play_turn(player, steps)
                if self.is_winner(player):
                    print(f"{player.name} wins!")
                    return

    def roll_dice(self):
        import random
        return random.randint(1, 6)


# Example usage
if __name__ == "__main__":
    board = Board(size=100)
    board.add_snake(Snake(start=16, end=6))
    board.add_snake(Snake(start=47, end=26))
    board.add_ladder(Ladder(start=3, end=22))
    board.add_ladder(Ladder(start=5, end=8))

    game = Game(board)
    player1 = Player(name="Alice")
    player2 = Player(name="Bob")

    game.add_player(player1)
    game.add_player(player2)

    game.play_game()
