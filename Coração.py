import turtle
import math
import random

frases = [
    "EU TE AMO", "I LOVE YOU", "TE AMO",
    "JE T'AIME", "TI AMO", "ICH LIEBE DICH",
    "愛してる", "사랑해", "我爱你",
    "Я ТЕБЯ ЛЮБЛЮ", "أحبك", "TE QUIERO",
    "SENI SEVIYORUM", "ILY", "LOVE ❤️"
]

tela = turtle.Screen()
tela.setup(width=1.0, height=1.0)  # Tela cheia
tela.bgcolor("black")
tela.title("Um coração para você ❤️")
tela.tracer(0)

caneta = turtle.Turtle()
caneta.hideturtle()
caneta.penup()
caneta.speed(0)

cores = ["red", "deeppink", "hotpink", "white", "magenta"]

# Gerar pontos do coração em ordem paramétrica (t de 0 a 2*pi) para desenhar contornando de forma organizada
pontos = []
passos = 600 # Quantidade ideal para conseguir ler com calma
for i in range(passos):
    t = (i / passos) * 2 * math.pi
    x = 16 * math.sin(t)**3
    y = (13 * math.cos(t) - 5 * math.cos(2*t)
         - 2 * math.cos(3*t) - math.cos(4*t))
    
    # Aumentar um pouco a escala para preencher bem a tela cheia
    pontos.append((x * 28, y * 28))

# Função de animação mais lenta e em ordem para dar tempo de ler
def desenhar_coracao(indice=0):
    if indice < len(pontos):
        x, y = pontos[indice]
        caneta.goto(x, y)
        caneta.color(random.choice(cores))
        frase = frases[indice % len(frases)] # Usa os idiomas em sequência ou aleatório
        caneta.write(frase, align="center", font=("Arial", 9, "bold"))
        
        tela.update()
        # Tempo maior entre cada palavra para ficar bem lento e legível (ex: 45 milissegundos)
        tela.ontimer(lambda: desenhar_coracao(indice + 1), 45)

# Iniciar animação
desenhar_coracao()
tela.mainloop()
