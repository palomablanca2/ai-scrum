import pygame
import random
import sys
import socket
import threading
import json
from datetime import datetime
import os

# Initialisatie
pygame.init()
pygame.font.init()

# Scherm instellingen
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Digitaal Ganzenbord")

# Kleuren
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (200, 200, 200)

# Fonts
font = pygame.font.SysFont('Arial', 24)
title_font = pygame.font.SysFont('Arial', 36)

# Spelvariabelen
class Game:
    def __init__(self):
        self.state = "menu"  # menu, singleplayer, multiplayer, game
        self.players = []
        self.current_player = 0
        self.dice_value = 0
        self.board = self.create_board()
        self.messages = []
        self.game_id = None
        self.server = None
        self.client = None
        self.ai_difficulty = "medium"
        self.saved_games = self.load_saved_games()

    def create_board(self):
        # Creëer een ganzenbord met speciale vakjes
        board = [{"type": "normal"} for _ in range(64)]
        
        # Speciale vakjes
        specials = {
            6: {"type": "bridge", "move_to": 12},
            19: {"type": "goose"},
            31: {"type": "goose"},
            42: {"type": "goose"},
            52: {"type": "goose"},
            58: {"type": "goose"},
            23: {"type": "jail", "skip_turns": 1},
            42: {"type": "maze", "move_back": 10},
            56: {"type": "death", "move_to": 1}
        }
        
        for pos, data in specials.items():
            if pos < len(board):
                board[pos] = data
                
        return board

    def load_saved_games(self):
        if os.path.exists("saved_games.json"):
            with open("saved_games.json", "r") as f:
                return json.load(f)
        return {}

    def save_game(self):
        if not self.game_id:
            self.game_id = str(datetime.now().timestamp())
        
        game_data = {
            "players": [{"name": p.name, "position": p.position} for p in self.players],
            "current_player": self.current_player,
            "board": self.board,
            "messages": self.messages[-10:]  # Laatste 10 berichten
        }
        
        self.saved_games[self.game_id] = game_data
        
        with open("saved_games.json", "w") as f:
            json.dump(self.saved_games, f)

    def roll_dice(self):
        return random.randint(1, 6)

    def ai_move(self):
        # Eenvoudige AI logica op basis van moeilijkheidsgraad
        dice = self.roll_dice()
        self.dice_value = dice
        
        player = self.players[self.current_player]
        new_pos = player.position + dice
        
        # Speciale vakjes verwerken
        if new_pos < len(self.board):
            cell = self.board[new_pos]
            
            if cell["type"] == "bridge":
                new_pos = cell["move_to"]
            elif cell["type"] == "goose":
                new_pos += dice  # Ga nogmaals vooruit
            elif cell["type"] == "jail":
                player.skip_turns = cell["skip_turns"]
            elif cell["type"] == "maze":
                new_pos -= cell["move_back"]
            elif cell["type"] == "death":
                new_pos = cell["move_to"]
        
        player.position = min(new_pos, 63)  # Maximaal vakje 63
        
        # Controleer winnaar
        if player.position == 63:
            self.messages.append(f"{player.name} heeft gewonnen!")
            self.state = "game_over"
        else:
            self.next_player()

    def next_player(self):
        self.current_player = (self.current_player + 1) % len(self.players)
        
        # Sla beurt over indien nodig
        while self.players[self.current_player].skip_turns > 0:
            self.players[self.current_player].skip_turns -= 1
            self.messages.append(f"{self.players[self.current_player].name} slaat een beurt over")
            self.current_player = (self.current_player + 1) % len(self.players)
        
        # AI beurt in singleplayer
        if self.state == "singleplayer" and self.current_player == 1:
            pygame.time.set_timer(AI_MOVE_EVENT, 1500)  # AI wacht 1.5 sec

class Player:
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.position = 0
        self.skip_turns = 0

# Netwerkfunctionaliteit
class GameServer:
    def __init__(self, game):
        self.game = game
        self.clients = []
        self.running = False
        
    def start(self, port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('0.0.0.0', port))
        self.server.listen()
        self.running = True
        threading.Thread(target=self.accept_connections, daemon=True).start()
        
    def accept_connections(self):
        while self.running:
            conn, addr = self.server.accept()
            self.clients.append(conn)
            threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
            
    def handle_client(self, conn):
        while self.running:
            try:
                data = conn.recv(1024).decode()
                if data:
                    self.process_message(conn, json.loads(data))
            except:
                break
                
    def process_message(self, conn, message):
        # Verwerk inkomende berichten van clients
        pass
        
    def broadcast(self, message):
        # Stuur bericht naar alle clients
        pass

class GameClient:
    def __init__(self, game):
        self.game = game
        self.socket = None
        self.running = False
        
    def connect(self, host, port=5555):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        self.running = True
        threading.Thread(target=self.receive_messages, daemon=True).start()
        
    def receive_messages(self):
        while self.running:
            try:
                data = self.socket.recv(1024).decode()
                if data:
                    self.game.process_network_message(json.loads(data))
            except:
                break
                
    def send(self, message):
        self.socket.send(json.dumps(message).encode())

# Events
AI_MOVE_EVENT = pygame.USEREVENT + 1

# Hoofdgame
game = Game()

def draw_menu():
    screen.fill(WHITE)
    
    # Titel
    title = title_font.render("Digitaal Ganzenbord", True, BLACK)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    # Knoppen
    singleplayer_btn = pygame.Rect(WIDTH//2 - 100, 150, 200, 50)
    multiplayer_btn = pygame.Rect(WIDTH//2 - 100, 220, 200, 50)
    load_btn = pygame.Rect(WIDTH//2 - 100, 290, 200, 50)
    
    pygame.draw.rect(screen, BLUE, singleplayer_btn)
    pygame.draw.rect(screen, GREEN, multiplayer_btn)
    pygame.draw.rect(screen, YELLOW, load_btn)
    
    single_text = font.render("Singleplayer", True, WHITE)
    multi_text = font.render("Multiplayer", True, WHITE)
    load_text = font.render("Laad Spel", True, WHITE)
    
    screen.blit(single_text, (singleplayer_btn.x + 50, singleplayer_btn.y + 15))
    screen.blit(multi_text, (multiplayer_btn.x + 50, multiplayer_btn.y + 15))
    screen.blit(load_text, (load_btn.x + 60, load_btn.y + 15))
    
    return singleplayer_btn, multiplayer_btn, load_btn

def draw_game():
    screen.fill(WHITE)
    
    # Teken bord
    board_width = 600
    board_height = 600
    board_x = (WIDTH - board_width) // 2
    board_y = (HEIGHT - board_height) // 2
    
    pygame.draw.rect(screen, GRAY, (board_x, board_y, board_width, board_height))
    
    # Teken vakjes en spelers
    # (vereist meer gedetailleerde implementatie)
    
    # Teken dobbelsteen
    dice_x, dice_y = 50, HEIGHT - 150
    pygame.draw.rect(screen, WHITE, (dice_x, dice_y, 100, 100))
    if game.dice_value > 0:
        dice_text = font.render(str(game.dice_value), True, BLACK)
        screen.blit(dice_text, (dice_x + 40, dice_y + 35))
    
    # Teken actieve speler
    current_player = game.players[game.current_player]
    player_text = font.render(f"Beurt: {current_player.name}", True, BLACK)
    screen.blit(player_text, (50, 50))
    
    # Teken chat
    pygame.draw.rect(screen, GRAY, (WIDTH - 250, 50, 200, 200))
    for i, msg in enumerate(game.messages[-8:]):
        msg_text = font.render(msg, True, BLACK)
        screen.blit(msg_text, (WIDTH - 240, 60 + i * 25))
    
    # Teken knoppen
    if game.state != "game_over" and game.current_player == 0:  # Alleen menselijke speler
        roll_btn = pygame.Rect(dice_x, dice_y - 60, 100, 40)
        pygame.draw.rect(screen, BLUE, roll_btn)
        roll_text = font.render("Gooi", True, WHITE)
        screen.blit(roll_text, (roll_btn.x + 35, roll_btn.y + 10))
        
        return roll_btn
    return None

def draw_player_selection():
    screen.fill(WHITE)
    
    title = title_font.render("Speler Setup", True, BLACK)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    name_text = font.render("Voer je naam in:", True, BLACK)
    screen.blit(name_text, (WIDTH//2 - 100, 150))
    
    name_input = pygame.Rect(WIDTH//2 - 100, 180, 200, 40)
    pygame.draw.rect(screen, WHITE, name_input, 2)
    
    start_btn = pygame.Rect(WIDTH//2 - 50, 250, 100, 40)
    pygame.draw.rect(screen, GREEN, start_btn)
    start_text = font.render("Start", True, WHITE)
    screen.blit(start_text, (start_btn.x + 30, start_btn.y + 10))
    
    return name_input, start_btn

def draw_multiplayer_menu():
    screen.fill(WHITE)
    
    title = title_font.render("Multiplayer", True, BLACK)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    host_btn = pygame.Rect(WIDTH//2 - 100, 150, 200, 50)
    join_btn = pygame.Rect(WIDTH//2 - 100, 220, 200, 50)
    
    pygame.draw.rect(screen, BLUE, host_btn)
    pygame.draw.rect(screen, GREEN, join_btn)
    
    host_text = font.render("Host Spel", True, WHITE)
    join_text = font.render("Deelnemen", True, WHITE)
    
    screen.blit(host_text, (host_btn.x + 60, host_btn.y + 15))
    screen.blit(join_text, (join_btn.x + 60, join_btn.y + 15))
    
    return host_btn, join_btn

# Hoofdgame loop
def main():
    clock = pygame.time.Clock()
    name_input_active = False
    player_name = ""
    input_rect = None
    roll_btn = None
    
    while True:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if game.state in ["singleplayer", "multiplayer"]:
                    game.save_game()
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                if game.state == "menu":
                    single_btn, multi_btn, load_btn = draw_menu()
                    if single_btn.collidepoint(mouse_pos):
                        game.state = "player_selection"
                        game.players = []
                    elif multi_btn.collidepoint(mouse_pos):
                        game.state = "multiplayer_menu"
                    elif load_btn.collidepoint(mouse_pos):
                        # Laad spel logica
                        pass
                        
                elif game.state == "player_selection":
                    input_rect, start_btn = draw_player_selection()
                    if input_rect.collidepoint(mouse_pos):
                        name_input_active = True
                    else:
                        name_input_active = False
                        
                    if start_btn.collidepoint(mouse_pos) and player_name:
                        game.players.append(Player(player_name, RED))
                        game.players.append(Player("Computer", BLUE))  # AI speler
                        game.state = "singleplayer"
                        game.messages.append("Spel gestart!")
                        
                elif game.state == "game" and roll_btn and roll_btn.collidepoint(mouse_pos):
                    game.dice_value = game.roll_dice()
                    player = game.players[game.current_player]
                    new_pos = player.position + game.dice_value
                    
                    # Verwerk speciale vakjes
                    if new_pos < len(game.board):
                        cell = game.board[new_pos]
                        
                        if cell["type"] == "bridge":
                            new_pos = cell["move_to"]
                            game.messages.append(f"{player.name} kwam op een brug en gaat naar vakje {new_pos}!")
                        elif cell["type"] == "goose":
                            new_pos += game.dice_value
                            game.messages.append(f"{player.name} kwam op een gans en gaat nogmaals vooruit!")
                        elif cell["type"] == "jail":
                            player.skip_turns = cell["skip_turns"]
                            game.messages.append(f"{player.name} is in de gevangenis en slaat {player.skip_turns} beurt(en) over!")
                        elif cell["type"] == "maze":
                            new_pos -= cell["move_back"]
                            game.messages.append(f"{player.name} is in het doolhof en gaat terug naar vakje {new_pos}!")
                        elif cell["type"] == "death":
                            new_pos = cell["move_to"]
                            game.messages.append(f"{player.name} is dood en gaat terug naar start!")
                    
                    player.position = min(new_pos, 63)
                    
                    # Controleer winnaar
                    if player.position == 63:
                        game.messages.append(f"{player.name} heeft gewonnen!")
                        game.state = "game_over"
                    else:
                        game.next_player()
                        
                elif game.state == "multiplayer_menu":
                    host_btn, join_btn = draw_multiplayer_menu()
                    if host_btn.collidepoint(mouse_pos):
                        game.server = GameServer(game)
                        game.server.start()
                        game.state = "player_selection"
                    elif join_btn.collidepoint(mouse_pos):
                        # Implementeer join logica
                        pass
                        
            if event.type == pygame.KEYDOWN and name_input_active:
                if event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                else:
                    player_name += event.unicode
                    
            if event.type == AI_MOVE_EVENT and game.state == "singleplayer":
                pygame.time.set_timer(AI_MOVE_EVENT, 0)  # Stop de timer
                game.ai_move()
        
        # Tekenen
        if game.state == "menu":
            draw_menu()
        elif game.state == "player_selection":
            input_rect, start_btn = draw_player_selection()
            
            # Toon ingevoerde naam
            name_surface = font.render(player_name, True, BLACK)
            screen.blit(name_surface, (input_rect.x + 5, input_rect.y + 5))
            input_rect.w = max(200, name_surface.get_width() + 10)
            
        elif game.state == "multiplayer_menu":
            draw_multiplayer_menu()
        elif game.state in ["singleplayer", "multiplayer", "game_over"]:
            roll_btn = draw_game()
        
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()