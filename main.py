import tkinter as tk
from tkinter import Canvas, Label, Button, messagebox
import cv2
import numpy as np
import pyautogui
import time
import threading
import keyboard
from PIL import ImageGrab, Image, ImageTk
import os

class MemoryGameBot:
    def __init__(self, root):
        self.root = root
        self.root.title("Bot Automático - Jogo da Memória")
        self.root.geometry("800x600")
        self.root.attributes("-topmost", True)
        
        # Variáveis para áreas de jogo
        self.card_area = None
        self.reward_area = None
        self.grid_positions = []
        self.reward_positions = []
        
        # Controle de jogo
        self.running = False
        self.paused = False
        self.card_images = {}
        self.matched_cards = set()
        self.known_cards = {}  # Armazena as cartas já vistas
        self.card_pairs = {}   # Armazena os pares de cartas identificados
        
        # Configuração do intervalo de tempo entre ações
        self.action_delay = 1.25  # Segundos entre ações
        
        # Criação da interface
        self.create_widgets()
        
        # Registrar tecla de parada
        keyboard.add_hotkey('f7', self.stop_bot)

        if not os.path.exists("./capturedCards"):
            os.makedirs("./capturedCards")
        
    def create_widgets(self):
        # Frame de controle
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)
        
        # Botões de configuração
        Button(control_frame, text="Selecionar Área de Cartas", command=self.select_card_area).pack(side=tk.LEFT, padx=5)
        Button(control_frame, text="Selecionar Área de Referência", command=self.select_reward_area).pack(side=tk.LEFT, padx=5)
        Button(control_frame, text="Iniciar Bot", command=self.start_bot).pack(side=tk.LEFT, padx=5)
        Button(control_frame, text="Parar Bot (F7)", command=self.stop_bot).pack(side=tk.LEFT, padx=5)
        
        # Área de status
        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=10, fill=tk.X)
        
        self.status_text = Label(status_frame, text="Aguardando configuração...")
        self.status_text.pack()
        
        # Área de log
        log_frame = tk.Frame(self.root)
        log_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        Label(log_frame, text="Log de Ações:").pack(anchor=tk.W)
        
        self.log_text = tk.Text(log_frame, height=20, width=80)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Barra de rolagem para o log
        scrollbar = tk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
    
    def select_card_area(self):
        """Permite ao usuário selecionar a área de cartas na tela"""
        self.status_text.config(text="Selecionando área de cartas...")
        
        result = self.select_area("cartas")
        
        if result:
            self.card_area = result
            self.status_text.config(text="Área de cartas selecionada")
            self.create_card_grid()
        else:
            self.status_text.config(text="Falha ao selecionar área de cartas!")
    
    def select_reward_area(self):
        """Permite ao usuário selecionar a área de referência na tela"""
        self.status_text.config(text="Selecionando área de referência...")
        
        result = self.select_area("referência")
        
        if result:
            self.reward_area = result
            self.status_text.config(text="Área de referência selecionada")
            self.create_reward_positions()
        else:
            self.status_text.config(text="Falha ao selecionar área de referência!")
    
    def select_area(self, area_type, center_size_percentage=0.1):
        """Interface para seleção de área na tela com proporção fixa e área central ignorada."""

        # Instruções para o usuário
        if area_type == "cartas":
            msg = f"Selecione a área retangular que contém as cartas do jogo.\n\n" \
                  f"A área central a ser ignorada será automaticamente definida como {center_size_percentage * 100}% do tamanho da carta."
        else:
            msg = "Selecione a área retangular que contém as recompensas/referências do jogo.\n\n"

        messagebox.showinfo("Seleção de Área", msg)

        self.area_coords = []
        self.ignore_center = False  # Indica se a área central deve ser ignorada
        self.center_coords = None  # Coordenadas da área central ignorada
        self.selection_complete = False
        self.rect = None

        # Janela de seleção semi-transparente
        self.selection_window = tk.Toplevel(self.root)
        self.selection_window.attributes("-fullscreen", True)
        self.selection_window.attributes("-alpha", 0.3)
        self.selection_canvas = Canvas(self.selection_window, bg="black")
        self.selection_canvas.pack(fill=tk.BOTH, expand=True)

        # Texto de instrução na tela
        self.selection_canvas.create_text(
            self.selection_window.winfo_screenwidth() // 2,
            50,
            text=f"Clique e arraste para selecionar a área de {area_type}",
            fill="white",
            font=("Arial", 16)
        )

        # Grade de orientação (linhas verticais e horizontais)
        self.grid_lines = []

        def start_selection(event):
            # Limpar linhas de grade anteriores
            for line in self.grid_lines:
                self.selection_canvas.delete(line)
            self.grid_lines = []

            self.area_coords = [event.x, event.y]
            if self.rect:
                self.selection_canvas.delete(self.rect)
            self.rect = self.selection_canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline="red", width=2
            )

        def update_selection(event):
            x1, y1 = self.area_coords
            x2, y2 = event.x, event.y

            # Atualizar o retângulo
            self.selection_canvas.coords(self.rect, x1, y1, x2, y2)

            # Limpar linhas de grade anteriores
            for line in self.grid_lines:
                self.selection_canvas.delete(line)
            self.grid_lines = []

        def end_selection(event):
            x1, y1 = self.area_coords
            x2, y2 = event.x, event.y

            # Garantir que x1 < x2 e y1 < y2
            if x2 < x1:
                x2, x1 = x1, x2
            if y2 < y1:
                y2, y1 = y1, y2

            self.area_coords = [x1, y1, x2, y2]
            self.selection_complete = True
            self.selection_window.destroy()

            # Se for a área de cartas, definir a área central ignorada automaticamente
            if area_type == "cartas":
                self.calculate_center_area(center_size_percentage)

        self.selection_canvas.bind("<ButtonPress-1>", start_selection)
        self.selection_canvas.bind("<B1-Motion>", update_selection)
        self.selection_canvas.bind("<ButtonRelease-1>", end_selection)

        # Tecla Escape para cancelar
        self.selection_window.bind("<Escape>", lambda e: self.selection_window.destroy())

        # Espera a janela de seleção fechar
        self.selection_window.wait_window(self.selection_window)

        # Retorna as coordenadas se a seleção foi concluída
        if self.selection_complete and len(self.area_coords) == 4:
            return tuple(self.area_coords)
        else:
            return None
    
    def create_card_grid(self):
        """Cria uma grade de posições 4x4 dentro da área selecionada"""
        if not self.card_area:
            return
        
        x1, y1, x2, y2 = self.card_area
        width = x2 - x1
        height = y2 - y1
        
        # Ajustar para uma grade quadrada
        size = min(width, height)
        x2 = x1 + size
        y2 = y1 + size
        self.card_area = (x1, y1, x2, y2)
        
        card_width = size / 4
        card_height = size / 4
        
        self.grid_positions = []
        for row in range(4):
            for col in range(4):
                pos_x = x1 + col * card_width
                pos_y = y1 + row * card_height
                self.grid_positions.append((
                    int(pos_x + card_width/2),  # Centro da carta (x)
                    int(pos_y + card_height/2),  # Centro da carta (y)
                    int(pos_x),  # Coordenada x1 para captura
                    int(pos_y),  # Coordenada y1 para captura
                    int(card_width),  # Largura da carta
                    int(card_height)   # Altura da carta
                ))
        
        # Mostrar visualização da grade
        self.show_grid_preview()
    
    def create_reward_positions(self):
        """Cria posições para as referências em grade 4x2"""
        if not self.reward_area:
            return
        
        x1, y1, x2, y2 = self.reward_area
        width = x2 - x1
        height = y2 - y1
        
        # Criar posições de referência (4x2)
        cols = 4
        rows = 2
        reward_width = width / cols
        reward_height = height / rows
        
        self.reward_positions = []
        for row in range(rows):
            for col in range(cols):
                pos_x = x1 + col * reward_width
                pos_y = y1 + row * reward_height
                
                # Índice da referência (0-7)
                reward_index = row * cols + col
                
                self.reward_positions.append((
                    int(pos_x + reward_width/2),  # Centro da referência (x)
                    int(pos_y + reward_height/2),  # Centro da referência (y)
                    int(pos_x),  # Coordenada x1 para captura
                    int(pos_y),  # Coordenada y1 para captura
                    int(reward_width),  # Largura
                    int(reward_height),  # Altura
                    reward_index  # Índice da referência
                ))
        
        # Mostrar visualização da grade de referências
        self.show_reward_preview()
    
    def show_grid_preview(self):
        """Mostra uma prévia da grade de cartas"""
        if not self.card_area:
            return
            
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Prévia da Grade de Cartas")
        preview_window.attributes("-topmost", True)
        
        x1, y1, x2, y2 = self.card_area
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        screenshot = screenshot.resize((400, 400), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(screenshot)
        
        # Manter referência para evitar coleta de lixo
        preview_window.tk_img = tk_img
        
        canvas = Canvas(preview_window, width=400, height=400)
        canvas.pack()
        
        # Desenhar a imagem
        canvas.create_image(0, 0, anchor="nw", image=tk_img)
        
        # Desenhar a grade
        for i in range(1, 4):
            # Linhas horizontais
            canvas.create_line(0, i * 100, 400, i * 100, fill="red", width=2)
            # Linhas verticais
            canvas.create_line(i * 100, 0, i * 100, 400, fill="red", width=2)
        
        # Numerar as posições
        for row in range(4):
            for col in range(4):
                pos = row * 4 + col
                canvas.create_text(
                    col * 100 + 50,
                    row * 100 + 50,
                    text=str(pos),
                    fill="white",
                    font=("Arial", 14, "bold")
                )
        
        Label(preview_window, text="Grade 4x4 de cartas definida. Feche esta janela para continuar.").pack(pady=10)
        Button(preview_window, text="OK", command=preview_window.destroy).pack(pady=10)
    
    def show_reward_preview(self):
        """Mostra uma prévia da área de referências 4x2"""
        if not self.reward_area:
            return
            
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Prévia da Área de Referência")
        preview_window.attributes("-topmost", True)
        
        x1, y1, x2, y2 = self.reward_area
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        
        # Redimensionar mantendo a proporção
        width, height = screenshot.size
        new_width = 400
        new_height = int((new_width / width) * height)
        
        screenshot = screenshot.resize((new_width, new_height), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(screenshot)
        
        # Manter referência para evitar coleta de lixo
        preview_window.tk_img = tk_img
        
        canvas = Canvas(preview_window, width=new_width, height=new_height)
        canvas.pack()
        
        # Desenhar a imagem
        canvas.create_image(0, 0, anchor="nw", image=tk_img)
        
        # Desenhar linhas de grade 4x2
        cell_width = new_width / 4
        cell_height = new_height / 2
        
        # Linhas verticais (3 divisórias = 4 colunas)
        for i in range(1, 4):
            canvas.create_line(
                i * cell_width, 0, 
                i * cell_width, new_height, 
                fill="red", width=2
            )
        
        # Linha horizontal do meio (1 divisória = 2 linhas)
        canvas.create_line(
            0, cell_height, 
            new_width, cell_height, 
            fill="red", width=2
        )
        
        # Numerar as posições
        for row in range(2):
            for col in range(4):
                pos = row * 4 + col
                canvas.create_text(
                    col * cell_width + cell_width/2,
                    row * cell_height + cell_height/2,
                    text=str(pos),
                    fill="white",
                    font=("Arial", 14, "bold")
                )
        
        Label(preview_window, text="Grade 4x2 de referências definida. Feche esta janela para continuar.").pack(pady=10)
        Button(preview_window, text="OK", command=preview_window.destroy).pack(pady=10)
    
    def start_bot(self):
        """Inicia o bot em uma thread separada"""
        if not self.card_area or not self.reward_area:
            messagebox.showerror("Erro", "Você precisa selecionar as áreas de cartas e referências primeiro!")
            return
        
        if self.running:
            messagebox.showinfo("Aviso", "O bot já está em execução!")
            return
        
        self.running = True
        self.paused = False
        self.matched_cards = set()
        self.known_cards = {}
        self.card_pairs = {}
        
        self.status_text.config(text="Bot iniciado - Pressione F7 para parar")
        self.log("Bot iniciado")
        
        # Iniciar o bot em uma thread separada
        self.bot_thread = threading.Thread(target=self.run_bot)
        self.bot_thread.daemon = True
        self.bot_thread.start()
    
    def stop_bot(self):
        """Para a execução do bot"""
        if self.running:
            self.running = False
            self.paused = False
            self.status_text.config(text="Bot parado")
            self.log("Bot parado")
    
    def log(self, message):
        """Adiciona uma mensagem ao log"""
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
    
    def capture_card_image(self, position):
        """Captura a imagem de uma carta na posição específica e salva em arquivo."""
        if position >= len(self.grid_positions):
            return None
        
        _, _, x, y, width, height = self.grid_positions[position]
        screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
        img_array = np.array(screenshot)
        
        # Salvar a imagem em um arquivo
        cv2.imwrite(os.path.join("./capturedCards", f"card_{position}.png"), cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))
        
        return img_array
    
    def compare_images(self, img1, img2, basePos, comparePos):
        """Compara duas imagens para verificar se são a mesma carta."""
        if img1 is None or img2 is None:
            return False
        
        # Converter para escala de cinza
        img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Redimensionar para garantir o mesmo tamanho
        img1_gray = cv2.resize(img1_gray, (100, 100))
        img2_gray = cv2.resize(img2_gray, (100, 100))
        
        # Calcular a diferença entre as imagens
        similarity = cv2.matchTemplate(img1_gray, img2_gray, cv2.TM_CCOEFF_NORMED)
        max_similarity = np.max(similarity)
        
        # log
        self.log(f"similarity na carta {basePos} - {comparePos} :({max_similarity})")

        # Considerar igual se a similaridade for maior que 0.85 (valor ajustado)
        return max_similarity > 0.85
    
    def click_card(self, position):
        """Clica em uma carta na posição especificada e move o mouse."""
        if position >= len(self.grid_positions):
            return
        
        x, y, _, _, _, _ = self.grid_positions[position]
        self.log(f"Clicando na carta {position} (x={x}, y={y})")
        pyautogui.click(x, y)
        
        # Mover o mouse para fora da área das cartas
        self.move_mouse_away()

    def move_mouse_away(self):
        """Move o mouse para uma posição fora da área das cartas."""
        x = 100
        y = 100
        pyautogui.moveTo(x, y)    
    
    def run_bot(self):
        """Lógica principal do bot"""
        try:
            # Inicializar o jogo
            self.log("Iniciando partida...")
            time.sleep(self.action_delay)  # Pequena pausa para o jogo iniciar
            
            # Primeiro passo: descobrir e memorizar todas as cartas
            self.discover_all_cards()
            
            # Segundo passo: combinar os pares identificados
            self.match_all_pairs()
            
            # Concluir o jogo
            self.log("Jogo concluído!")
            self.status_text.config(text="Jogo concluído")
            
        except Exception as e:
            self.log(f"Erro: {str(e)}")
        finally:
            self.running = False
    
    def discover_all_cards(self):
        """Revela e memoriza todas as cartas do jogo"""
        self.log("Fase 1: Descobrindo todas as cartas")
        
        # Lista de posições que ainda não foram verificadas
        positions_to_check = list(range(16))
        
        while self.running and positions_to_check:
            # Selecionar a primeira carta da rodada
            first_card_pos = positions_to_check.pop(0)
            
            # Pular se a carta já foi combinada
            if first_card_pos in self.matched_cards:
                continue
                
            self.log(f"Clicando na primeira carta da rodada: {first_card_pos}")
            self.click_card(first_card_pos)
            time.sleep(self.action_delay)
            
            # Capturar a imagem da primeira carta
            first_card_image = self.capture_card_image(first_card_pos)
            self.card_images[first_card_pos] = first_card_image
            
            # Verificar se já existe um par para esta carta
            found_match = False
            match_pos = None
            
            for pos, img in self.card_images.items():
                if pos != first_card_pos and pos not in self.matched_cards:
                    if self.compare_images(first_card_image, img, first_card_pos, pos):
                        found_match = True
                        match_pos = pos
                        
                        # Registrar o par identificado
                        if first_card_pos not in self.card_pairs:
                            self.card_pairs[first_card_pos] = match_pos
                        if match_pos not in self.card_pairs:
                            self.card_pairs[match_pos] = first_card_pos
                            
                        self.log(f"Identificado par para a carta {first_card_pos}: carta {match_pos}")
                        break
            
            # Selecionar a segunda carta da rodada
            if len(positions_to_check) > 0:
                second_card_pos = positions_to_check.pop(0)
                
                # Pular se a carta já foi combinada
                while second_card_pos in self.matched_cards and positions_to_check:
                    second_card_pos = positions_to_check.pop(0)
                
                if second_card_pos not in self.matched_cards:
                    self.log(f"Clicando na segunda carta da rodada: {second_card_pos}")
                    self.click_card(second_card_pos)
                    time.sleep(self.action_delay)
                    
                    # Capturar a imagem da segunda carta
                    second_card_image = self.capture_card_image(second_card_pos)
                    self.card_images[second_card_pos] = second_card_image
                    
                    # Verificar se formam um par
                    if self.compare_images(first_card_image, second_card_image, first_card_pos, second_card_pos):
                        self.log(f"Par encontrado: cartas {first_card_pos} e {second_card_pos}")
                        
                        # Registrar o par identificado
                        self.card_pairs[first_card_pos] = second_card_pos
                        self.card_pairs[second_card_pos] = first_card_pos
                        
                        # Marcar ambas as cartas como combinadas (para não clicar nelas novamente durante a descoberta)
                        self.matched_cards.add(first_card_pos)
                        self.matched_cards.add(second_card_pos)
                    else:
                        # Verificar se a segunda carta forma par com alguma carta já conhecida
                        for pos, img in self.card_images.items():
                            if pos != second_card_pos and pos not in self.matched_cards:
                                if self.compare_images(second_card_image, img, second_card_pos, pos):
                                    self.log(f"Identificado par para a carta {second_card_pos}: carta {pos}")
                                    
                                    # Registrar o par identificado
                                    self.card_pairs[second_card_pos] = pos
                                    self.card_pairs[pos] = second_card_pos
                                    break
            
            # Aguardar antes da próxima rodada
            time.sleep(self.action_delay)
        
        # Limpar o conjunto de cartas combinadas para a próxima fase
        self.matched_cards = set()
        self.log("Fase de descoberta concluída")
    
    def match_all_pairs(self):
        """Combina todos os pares de cartas identificados"""
        self.log("Fase 2: Combinando todos os pares")
        
        # Lista de cartas ainda não combinadas
        cards_to_match = [i for i in range(16) if i not in self.matched_cards]
        
        while self.running and len(self.matched_cards) < 16:
            # Selecionar uma carta que ainda não foi combinada
            if not cards_to_match:
                self.log("Todas as cartas foram combinadas!")
                break
                
            card1 = cards_to_match.pop(0)
            
            # Pular se a carta já foi combinada
            if card1 in self.matched_cards:
                continue
            
            # Verificar se temos um par conhecido para esta carta
            if card1 in self.card_pairs:
                card2 = self.card_pairs[card1]
                
                # Verificar se o par ainda não foi combinado
                if card2 not in self.matched_cards:
                    self.log(f"Combinando o par de cartas {card1} e {card2}")
                    
                    # Clicar na primeira carta
                    self.click_card(card1)
                    time.sleep(self.action_delay)
                    
                    # Clicar na segunda carta
                    self.click_card(card2)
                    time.sleep(self.action_delay)
                    
                    # Marcar ambas as cartas como combinadas
                    self.matched_cards.add(card1)
                    self.matched_cards.add(card2)
                    
                    # Remover a segunda carta da lista de pendentes, se estiver lá
                    if card2 in cards_to_match:
                        cards_to_match.remove(card2)
                    
                    # Aguardar antes da próxima combinação
                    time.sleep(self.action_delay)
            else:
                # Se não conhecemos o par, tentar descobrir
                self.log(f"Não foi encontrado par para a carta {card1}, tentando descobrir...")
                
                # Clicar na primeira carta
                self.click_card(card1)
                time.sleep(self.action_delay)
                
                # Tentar as cartas restantes uma a uma
                for card2 in cards_to_match:
                    if card2 != card1 and card2 not in self.matched_cards:
                        # Clicar na carta candidata
                        self.click_card(card2)
                        time.sleep(self.action_delay)
                        
                        # Se formarem um par, elas serão automaticamente combinadas
                        # Atualizar o estado
                        self.matched_cards.add(card1)
                        self.matched_cards.add(card2)
                        if card2 in cards_to_match:
                            cards_to_match.remove(card2)
                        
                        self.log(f"Par encontrado: cartas {card1} e {card2}")
                        break
                        
                # Aguardar antes da próxima tentativa
                time.sleep(self.action_delay)
        
        self.log("Fase de combinação concluída")

# Função principal
def main():
    root = tk.Tk()
    app = MemoryGameBot(root)
    root.mainloop()

if __name__ == "__main__":
    main()
