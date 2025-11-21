# web_server.py - ПОЛНАЯ ВЕРСИЯ ДЛЯ PYTHONANYWHERE
import asyncio
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from datetime import datetime
import socket

# Файл для хранения статистики
STATS_FILE = "stats_data.json"

def load_stats():
    """Загружает статистику из файла"""
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки статистики: {e}")
    return {}

# Загружаем статистику при запуске
stats_storage = load_stats()

class StatsHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        # Добавляем заголовки против кэширования
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        
        # Обрабатываем запросы к /stats/{id}
        if self.path.startswith('/stats/'):
            stats_id = self.path.split('/')[-1]
            self.serve_stats_page(stats_id)
        elif self.path == '/':
            self.serve_welcome_page()
        else:
            self.serve_404()
    
    def serve_stats_page(self, stats_id):
        # Перезагружаем статистику из файла при каждом запросе
        current_stats = load_stats()
        
        if stats_id not in current_stats:
            self.serve_404()
            return
        
        stats_data = current_stats[stats_id]
        
        # Генерируем HTML страницу
        html = self.generate_stats_html(stats_data)
        
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_welcome_page(self):
        html = """
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Celestial Checker</title>
            <style>
                :root {
                    --glass-autumn: rgba(139, 69, 19, 0.18);
                    --glass-autumn-light: rgba(160, 82, 45, 0.12);
                    --glass-autumn-dark: rgba(101, 67, 33, 0.2);
                    --glass-border: rgba(210, 105, 30, 0.25);
                    --glass-shadow: 0 8px 32px rgba(101, 67, 33, 0.1);
                    --glass-blur: blur(20px);
                    --text-autumn: rgba(255, 253, 208, 0.95);
                    --text-autumn-light: rgba(255, 253, 208, 0.7);
                    --text-autumn-gold: rgba(255, 215, 0, 0.9);
                }
                
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
                    min-height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    color: var(--text-autumn);
                    padding: 20px;
                    position: relative;
                    overflow: hidden;
                    cursor: default;
                }

                /* Autumn Parallax Layers */
                .layers {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    z-index: -3;
                    overflow: hidden;
                }

                .layers__container {
                    transform-style: preserve-3d;
                    transform: rotateX(var(--move-y)) rotateY(var(--move-x));
                    will-change: transform;
                    transition: transform 0.3s ease-out;
                    position: relative;
                    width: 100%;
                    height: 100%;
                }

                .layers__item {
                    position: absolute;
                    inset: -5vw;
                    background-size: cover;
                    background-position: center;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .layer-1 {
                    background-image: url('https://img10.joyreactor.cc/pics/post/full/OreGairu-Anime-Isshiki-Iroha-5139586.jpeg');
                    transform: translateZ(-40px) scale(1.2);
                    filter: blur(15px) brightness(0.6) contrast(1.1) sepia(0.3) hue-rotate(-10deg);
                }

                .layer-2 {
                    background-image: url('https://img10.joyreactor.cc/pics/post/full/OreGairu-Anime-Isshiki-Iroha-5139586.jpeg');
                    transform: translateZ(-20px) scale(1.1);
                    filter: blur(8px) brightness(0.7) contrast(1.05) sepia(0.2) hue-rotate(-5deg);
                }

                .layer-3 {
                    transform: translateZ(0px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .layer-4 {
                    transform: translateZ(15px);
                    pointer-events: none;
                }

                .layer-5 {
                    background-image: url('https://img10.joyreactor.cc/pics/post/full/OreGairu-Anime-Isshiki-Iroha-5139586.jpeg');
                    transform: translateZ(30px) scale(0.95);
                    filter: blur(3px) brightness(0.8) contrast(1.02) sepia(0.1);
                }

                .layer-6 {
                    background-image: url('https://img10.joyreactor.cc/pics/post/full/OreGairu-Anime-Isshiki-Iroha-5139586.jpeg');
                    transform: translateZ(45px) scale(0.9);
                    filter: blur(1px) brightness(0.9);
                }

                /* Autumn Leaves Overlay */
                .autumn-leaves {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                    z-index: -1;
                    opacity: 0.7;
                }

                .leaf {
                    position: absolute;
                    background: linear-gradient(45deg, #ff6b35, #ff8e00, #ffaa00);
                    border-radius: 80% 0 80% 0;
                    opacity: 0.7;
                    animation: fall linear infinite;
                }

                .leaf::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(45deg, transparent 50%, rgba(255, 255, 255, 0.2) 50%);
                    border-radius: inherit;
                }

                .leaf-1 { width: 25px; height: 25px; animation-duration: 18s; left: 5%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }
                .leaf-2 { width: 20px; height: 20px; animation-duration: 22s; left: 10%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }
                .leaf-3 { width: 30px; height: 30px; animation-duration: 15s; left: 15%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }
                .leaf-4 { width: 22px; height: 22px; animation-duration: 25s; left: 20%; background: linear-gradient(45deg, #ffaa00, #ffc400); }
                .leaf-5 { width: 28px; height: 28px; animation-duration: 20s; left: 25%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }
                .leaf-6 { width: 24px; height: 24px; animation-duration: 17s; left: 30%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }
                .leaf-7 { width: 26px; height: 26px; animation-duration: 23s; left: 35%; background: linear-gradient(45deg, #ffaa00, #ffc400); }
                .leaf-8 { width: 21px; height: 21px; animation-duration: 19s; left: 40%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }
                .leaf-9 { width: 29px; height: 29px; animation-duration: 16s; left: 45%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }
                .leaf-10 { width: 23px; height: 23px; animation-duration: 21s; left: 50%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }
                .leaf-11 { width: 27px; height: 27px; animation-duration: 24s; left: 55%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }
                .leaf-12 { width: 19px; height: 19px; animation-duration: 18s; left: 60%; background: linear-gradient(45deg, #ffaa00, #ffc400); }
                .leaf-13 { width: 31px; height: 31px; animation-duration: 26s; left: 65%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }
                .leaf-14 { width: 22px; height: 22px; animation-duration: 19s; left: 70%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }
                .leaf-15 { width: 26px; height: 26px; animation-duration: 22s; left: 75%; background: linear-gradient(45deg, #ffaa00, #ffc400); }
                .leaf-16 { width: 24px; height: 24px; animation-duration: 20s; left: 80%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }
                .leaf-17 { width: 28px; height: 28px; animation-duration: 17s; left: 85%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }
                .leaf-18 { width: 20px; height: 20px; animation-duration: 25s; left: 90%; background: linear-gradient(45deg, #ffaa00, #ffc400); }
                .leaf-19 { width: 25px; height: 25px; animation-duration: 21s; left: 95%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }
                .leaf-20 { width: 30px; height: 30px; animation-duration: 16s; left: 98%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }

                @keyframes fall {
                    0% {
                        transform: translateY(-100px) rotate(0deg);
                        opacity: 0;
                    }
                    10% {
                        opacity: 0.7;
                    }
                    90% {
                        opacity: 0.7;
                    }
                    100% {
                        transform: translateY(100vh) rotate(360deg);
                        opacity: 0;
                    }
                }

                /* Light Overlay */
                .light-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: radial-gradient(circle at 20% 80%, rgba(255, 140, 0, 0.1) 0%, transparent 50%);
                    z-index: -2;
                    pointer-events: none;
                }

                /* Rain Canvas - Autumn Version */
                .rain {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                }

                /* Fog Effect - Autumn Version */
                .fog-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(139, 69, 19, 0.1);
                    backdrop-filter: blur(8px);
                    z-index: 100;
                    opacity: 0;
                    transition: opacity 3s ease-in-out;
                    pointer-events: none;
                }

                /* Glass Container - Autumn Theme - More Transparent */
                .glass-container {
                    background: var(--glass-autumn);
                    backdrop-filter: var(--glass-blur);
                    -webkit-backdrop-filter: var(--glass-blur);
                    border: 1px solid var(--glass-border);
                    border-radius: 24px;
                    padding: 50px 40px;
                    box-shadow: 
                        var(--glass-shadow),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    text-align: center;
                    max-width: 500px;
                    width: 100%;
                    position: relative;
                    overflow: hidden;
                    transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                    z-index: 10;
                }
                
                .glass-container:hover {
                    transform: scale(1.02);
                }
                
                .glass-container::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, 
                        transparent, 
                        rgba(255, 165, 0, 0.15), 
                        transparent);
                    transition: left 0.6s ease;
                }
                
                .glass-container:hover::before {
                    left: 100%;
                }
                
                .glass-icon {
                    font-size: 64px;
                    margin-bottom: 24px;
                    opacity: 0.9;
                    filter: drop-shadow(0 4px 8px rgba(101, 67, 33, 0.3));
                    transition: transform 0.3s ease;
                }
                
                .glass-container:hover .glass-icon {
                    transform: scale(1.1);
                }
                
                .glass-title {
                    font-size: 34px;
                    font-weight: 700;
                    margin-bottom: 16px;
                    color: var(--text-autumn);
                    letter-spacing: -0.5px;
                    text-shadow: 0 2px 4px rgba(101, 67, 33, 0.5);
                    transition: transform 0.3s ease;
                }
                
                .glass-container:hover .glass-title {
                    transform: scale(1.05);
                }
                
                .glass-subtitle {
                    font-size: 17px;
                    color: var(--text-autumn-light);
                    line-height: 1.4;
                    margin-bottom: 8px;
                    font-weight: 400;
                    text-shadow: 0 1px 2px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }
                
                .glass-container:hover .glass-subtitle {
                    transform: scale(1.03);
                }

                /* Autumn Pattern */
                .autumn-pattern {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-image: 
                        radial-gradient(circle at 20% 80%, rgba(255, 140, 0, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(210, 105, 30, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 40% 40%, rgba(139, 69, 19, 0.05) 0%, transparent 50%);
                    z-index: -1;
                    pointer-events: none;
                }
            </style>
        </head>
        <body>
            <!-- Autumn Parallax Layers -->
            <section class="layers">
                <div class="layers__container">
                    <div class="layers__item layer-1"></div>
                    <div class="layers__item layer-2"></div>
                    <div class="layers__item layer-3"></div>
                    <div class="layers__item layer-4">
                        <canvas class="rain"></canvas>
                    </div>
                    <div class="layers__item layer-5"></div>
                    <div class="layers__item layer-6"></div>
                </div>
            </section>

            <!-- Autumn Leaves -->
            <div class="autumn-leaves">
                <div class="leaf leaf-1"></div>
                <div class="leaf leaf-2"></div>
                <div class="leaf leaf-3"></div>
                <div class="leaf leaf-4"></div>
                <div class="leaf leaf-5"></div>
                <div class="leaf leaf-6"></div>
                <div class="leaf leaf-7"></div>
                <div class="leaf leaf-8"></div>
                <div class="leaf leaf-9"></div>
                <div class="leaf leaf-10"></div>
                <div class="leaf leaf-11"></div>
                <div class="leaf leaf-12"></div>
                <div class="leaf leaf-13"></div>
                <div class="leaf leaf-14"></div>
                <div class="leaf leaf-15"></div>
                <div class="leaf leaf-16"></div>
                <div class="leaf leaf-17"></div>
                <div class="leaf leaf-18"></div>
                <div class="leaf leaf-19"></div>
                <div class="leaf leaf-20"></div>
            </div>

            <!-- Light Overlay -->
            <div class="light-overlay"></div>

            <!-- Fog Effect -->
            <div class="fog-overlay" id="fogOverlay"></div>

            <!-- Autumn Pattern -->
            <div class="autumn-pattern"></div>
            
            <!-- Main Content -->
            <div class="glass-container">
                <div class="glass-icon">🍂</div>
                <h1 class="glass-title">Celestial Checker</h1>
                <p class="glass-subtitle">Веб-сервер для отображения статистики проверки аккаунтов</p>
                <p class="glass-subtitle">Используйте ссылку из Telegram бота для просмотра статистики</p>
            </div>

            <script>
                document.addEventListener('DOMContentLoaded', function() {
                    // Parallax Effect - Very subtle
                    const layersContainer = document.querySelector('.layers__container');
                    
                    function updateParallax(e) {
                        const moveX = (e.clientX - window.innerWidth / 2) * 0.0001;
                        const moveY = (e.clientY - window.innerHeight / 2) * 0.0001;
                        
                        document.documentElement.style.setProperty('--move-x', moveX + 'rad');
                        document.documentElement.style.setProperty('--move-y', moveY + 'rad');
                    }

                    document.addEventListener('mousemove', updateParallax);

                    // Enhanced Autumn Rain Effect
                    const canvas = document.querySelector('.rain');
                    if (!canvas) {
                        console.log('Canvas not found');
                        return;
                    }
                    
                    const ctx = canvas.getContext('2d');
                    let width = canvas.width = window.innerWidth;
                    let height = canvas.height = window.innerHeight;

                    class AutumnDrop {
                        constructor() {
                            this.reset();
                            this.z = Math.random() * 0.5 + 0.5;
                        }
                        
                        reset() {
                            this.x = Math.random() * width;
                            this.y = Math.random() * -height;
                            this.speed = Math.random() * 8 + 4;
                            this.length = Math.random() * 15 + 8;
                            this.opacity = Math.random() * 0.4 + 0.3;
                            this.wind = (Math.random() - 0.5) * 1.2;
                            this.size = Math.random() * 1.5 + 0.8;
                            // Autumn colors
                            this.color = Math.random() > 0.5 ? '255,140,0' : '210,105,30';
                        }
                        
                        update() {
                            this.y += this.speed * this.z;
                            this.x += this.wind * this.z;
                            
                            if (this.y > height) {
                                this.reset();
                                this.y = -20;
                            }
                        }
                        
                        draw() {
                            // Draw autumn drop
                            ctx.beginPath();
                            ctx.arc(this.x, this.y, this.size * this.z, 0, Math.PI * 2);
                            ctx.fillStyle = 'rgba(' + this.color + ', ' + (this.opacity * this.z) + ')';
                            ctx.fill();
                            
                            // Draw drop tail
                            if (this.z > 0.7) {
                                ctx.beginPath();
                                ctx.moveTo(this.x, this.y);
                                ctx.lineTo(this.x + this.wind * 3, this.y + this.length * this.z);
                                ctx.strokeStyle = 'rgba(' + this.color + ', ' + (this.opacity * this.z * 0.6) + ')';
                                ctx.lineWidth = 0.6 * this.z;
                                ctx.lineCap = 'round';
                                ctx.stroke();
                            }
                        }
                    }

                    // Enhanced Leaf particle effect
                    class LeafParticle {
                        constructor(x, y, z) {
                            this.x = x;
                            this.y = y;
                            this.z = z;
                            this.particles = [];
                            this.life = 1.0;
                            this.createParticles();
                        }
                        
                        createParticles() {
                            for (let i = 0; i < 5; i++) {
                                this.particles.push({
                                    x: this.x,
                                    y: this.y,
                                    vx: (Math.random() - 0.5) * 4 * this.z,
                                    vy: -Math.random() * 3 * this.z,
                                    life: 1.0,
                                    color: Math.random() > 0.5 ? '255,140,0' : '210,105,30'
                                });
                            }
                        }
                        
                        update() {
                            this.life -= 0.015;
                            this.particles.forEach(p => {
                                p.x += p.vx;
                                p.y += p.vy;
                                p.vy += 0.1;
                                p.life -= 0.02;
                            });
                            this.particles = this.particles.filter(p => p.life > 0);
                            return this.life > 0 && this.particles.length > 0;
                        }
                        
                        draw() {
                            this.particles.forEach(p => {
                                ctx.beginPath();
                                ctx.arc(p.x, p.y, 2 * this.z, 0, Math.PI * 2);
                                ctx.fillStyle = 'rgba(' + p.color + ', ' + (p.life * 0.5) + ')';
                                ctx.fill();
                            });
                        }
                    }

                    const autumnDrops = [];
                    const leafParticles = [];
                    const dropCount = 200;

                    for (let i = 0; i < dropCount; i++) {
                        autumnDrops.push(new AutumnDrop());
                    }

                    function animateAutumnRain() {
                        ctx.clearRect(0, 0, width, height);
                        
                        // Semi-transparent background for motion effect
                        ctx.fillStyle = 'rgba(101, 67, 33, 0.04)';
                        ctx.fillRect(0, 0, width, height);
                        
                        // Update and draw drops
                        autumnDrops.forEach(drop => {
                            const prevY = drop.y;
                            drop.update();
                            
                            // Check collision with ground - create leaf particles
                            if (prevY < height && drop.y >= height) {
                                leafParticles.push(new LeafParticle(drop.x, height, drop.z));
                            }
                            
                            drop.draw();
                        });
                        
                        // Update and draw leaf particles
                        for (let i = leafParticles.length - 1; i >= 0; i--) {
                            if (!leafParticles[i].update()) {
                                leafParticles.splice(i, 1);
                            } else {
                                leafParticles[i].draw();
                            }
                        }
                        
                        requestAnimationFrame(animateAutumnRain);
                    }

                    // Start autumn rain animation
                    animateAutumnRain();

                    // Fog Effect
                    const fogOverlay = document.getElementById('fogOverlay');
                    let fogTimer;

                    function startFogEffect() {
                        fogTimer = setInterval(() => {
                            // Random fog every 15-25 seconds
                            const delay = Math.random() * 10000 + 15000;
                            setTimeout(() => {
                                if (fogOverlay) {
                                    fogOverlay.style.opacity = '0.4';
                                    setTimeout(() => {
                                        fogOverlay.style.opacity = '0';
                                    }, 4000);
                                }
                            }, delay);
                        }, 35000); // Check every 35 seconds
                    }

                    startFogEffect();
                });

                // Event handlers outside DOMContentLoaded
                window.addEventListener('resize', () => {
                    const canvas = document.querySelector('.rain');
                    if (canvas) {
                        canvas.width = window.innerWidth;
                        canvas.height = window.innerHeight;
                    }
                });
            </script>
        </body>
        </html>
        """
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def generate_account_card(self, account, index):
        """Генерирует HTML карточку для аккаунта"""
        premium_badge = """
        <div class="premium-glass-badge">
            <span class="badge-icon">🍁</span>
            Premium
        </div>
        """ if account.get('premium') else ""
        
        return f"""
        <div class="account-glass-card" data-index="{index}">
            <div class="account-glass-header">
                <div class="account-glass-avatar">
                    <span class="avatar-icon">👤</span>
                </div>
                <div class="account-glass-info">
                    <div class="account-username">{account.get('username', 'Unknown')}</div>
                    <div class="account-user-id">ID: {account.get('user_id', 'N/A')}</div>
                </div>
                {premium_badge}
            </div>
            <div class="account-glass-stats">
                <div class="account-stat-item">
                    <div class="stat-icon">💰</div>
                    <div class="stat-value">{account.get('robux', 0):,}</div>
                    <div class="stat-label">Robux</div>
                </div>
                <div class="account-stat-divider"></div>
                <div class="account-stat-item">
                    <div class="stat-icon">🎁</div>
                    <div class="stat-value">{account.get('all_time_donate', 0):,}</div>
                    <div class="stat-label">Donated</div>
                </div>
                <div class="account-stat-divider"></div>
                <div class="account-stat-item">
                    <div class="stat-icon">🧠</div>
                    <div class="stat-value">{account.get('steal_a_brainrot_spent', 0):,}</div>
                    <div class="stat-label">Brainrot</div>
                </div>
            </div>
        </div>
        """
    
    def generate_stats_html(self, stats_data):
        accounts_html = "".join([self.generate_account_card(acc, i) for i, acc in enumerate(stats_data['accounts'])])
        
        html = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Celestial Checker - {stats_data['id']}</title>
            <style>
                :root {{
                    --glass-autumn: rgba(139, 69, 19, 0.18);
                    --glass-autumn-light: rgba(160, 82, 45, 0.12);
                    --glass-autumn-dark: rgba(101, 67, 33, 0.2);
                    --glass-border: rgba(210, 105, 30, 0.25);
                    --glass-shadow: 0 8px 32px rgba(101, 67, 33, 0.1);
                    --glass-shadow-elevated: 0 16px 48px rgba(101, 67, 33, 0.15);
                    --glass-blur: blur(30px);
                    --text-autumn: rgba(255, 253, 208, 0.95);
                    --text-autumn-light: rgba(255, 253, 208, 0.7);
                    --text-autumn-lighter: rgba(255, 253, 208, 0.5);
                    --text-autumn-gold: rgba(255, 215, 0, 0.9);
                }}
                
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
                    color: var(--text-autumn);
                    min-height: 100vh;
                    position: relative;
                    overflow-x: hidden;
                    cursor: default;
                }}

                /* Autumn Parallax Layers */
                .layers {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    z-index: -3;
                    overflow: hidden;
                }}

                .layers__container {{
                    transform-style: preserve-3d;
                    transform: rotateX(var(--move-y)) rotateY(var(--move-x));
                    will-change: transform;
                    transition: transform 0.3s ease-out;
                    position: relative;
                    width: 100%;
                    height: 100%;
                }}

                .layers__item {{
                    position: absolute;
                    inset: -5vw;
                    background-size: cover;
                    background-position: center;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}

                .layer-1 {{
                    background-image: url('https://img10.joyreactor.cc/pics/post/full/OreGairu-Anime-Isshiki-Iroha-5139586.jpeg');
                    transform: translateZ(-40px) scale(1.2);
                    filter: blur(15px) brightness(0.6) contrast(1.1) sepia(0.3) hue-rotate(-10deg);
                }}

                .layer-2 {{
                    background-image: url('https://img10.joyreactor.cc/pics/post/full/OreGairu-Anime-Isshiki-Iroha-5139586.jpeg');
                    transform: translateZ(-20px) scale(1.1);
                    filter: blur(8px) brightness(0.7) contrast(1.05) sepia(0.2) hue-rotate(-5deg);
                }}

                .layer-3 {{
                    transform: translateZ(0px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}

                .layer-4 {{
                    transform: translateZ(15px);
                    pointer-events: none;
                }}

                .layer-5 {{
                    background-image: url('https://img10.joyreactor.cc/pics/post/full/OreGairu-Anime-Isshiki-Iroha-5139586.jpeg');
                    transform: translateZ(30px) scale(0.95);
                    filter: blur(3px) brightness(0.8) contrast(1.02) sepia(0.1);
                }}

                .layer-6 {{
                    background-image: url('https://img10.joyreactor.cc/pics/post/full/OreGairu-Anime-Isshiki-Iroha-5139586.jpeg');
                    transform: translateZ(45px) scale(0.9);
                    filter: blur(1px) brightness(0.9);
                }}

                /* Autumn Leaves Overlay */
                .autumn-leaves {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                    z-index: -1;
                    opacity: 0.7;
                }}

                .leaf {{
                    position: absolute;
                    background: linear-gradient(45deg, #ff6b35, #ff8e00, #ffaa00);
                    border-radius: 80% 0 80% 0;
                    opacity: 0.7;
                    animation: fall linear infinite;
                }}

                .leaf::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(45deg, transparent 50%, rgba(255, 255, 255, 0.2) 50%);
                    border-radius: inherit;
                }}

                .leaf-1 {{ width: 25px; height: 25px; animation-duration: 18s; left: 5%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }}
                .leaf-2 {{ width: 20px; height: 20px; animation-duration: 22s; left: 10%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }}
                .leaf-3 {{ width: 30px; height: 30px; animation-duration: 15s; left: 15%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }}
                .leaf-4 {{ width: 22px; height: 22px; animation-duration: 25s; left: 20%; background: linear-gradient(45deg, #ffaa00, #ffc400); }}
                .leaf-5 {{ width: 28px; height: 28px; animation-duration: 20s; left: 25%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }}
                .leaf-6 {{ width: 24px; height: 24px; animation-duration: 17s; left: 30%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }}
                .leaf-7 {{ width: 26px; height: 26px; animation-duration: 23s; left: 35%; background: linear-gradient(45deg, #ffaa00, #ffc400); }}
                .leaf-8 {{ width: 21px; height: 21px; animation-duration: 19s; left: 40%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }}
                .leaf-9 {{ width: 29px; height: 29px; animation-duration: 16s; left: 45%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }}
                .leaf-10 {{ width: 23px; height: 23px; animation-duration: 21s; left: 50%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }}
                .leaf-11 {{ width: 27px; height: 27px; animation-duration: 24s; left: 55%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }}
                .leaf-12 {{ width: 19px; height: 19px; animation-duration: 18s; left: 60%; background: linear-gradient(45deg, #ffaa00, #ffc400); }}
                .leaf-13 {{ width: 31px; height: 31px; animation-duration: 26s; left: 65%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }}
                .leaf-14 {{ width: 22px; height: 22px; animation-duration: 19s; left: 70%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }}
                .leaf-15 {{ width: 26px; height: 26px; animation-duration: 22s; left: 75%; background: linear-gradient(45deg, #ffaa00, #ffc400); }}
                .leaf-16 {{ width: 24px; height: 24px; animation-duration: 20s; left: 80%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }}
                .leaf-17 {{ width: 28px; height: 28px; animation-duration: 17s; left: 85%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }}
                .leaf-18 {{ width: 20px; height: 20px; animation-duration: 25s; left: 90%; background: linear-gradient(45deg, #ffaa00, #ffc400); }}
                .leaf-19 {{ width: 25px; height: 25px; animation-duration: 21s; left: 95%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }}
                .leaf-20 {{ width: 30px; height: 30px; animation-duration: 16s; left: 98%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }}

                @keyframes fall {{
                    0% {{
                        transform: translateY(-100px) rotate(0deg);
                        opacity: 0;
                    }}
                    10% {{
                        opacity: 0.7;
                    }}
                    90% {{
                        opacity: 0.7;
                    }}
                    100% {{
                        transform: translateY(100vh) rotate(360deg);
                        opacity: 0;
                    }}
                }}

                /* Light Overlay */
                .light-overlay {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: radial-gradient(circle at 20% 80%, rgba(255, 140, 0, 0.1) 0%, transparent 50%);
                    z-index: -2;
                    pointer-events: none;
                }}

                /* Rain Canvas - Autumn Version */
                .rain {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                }}

                /* Fog Effect - Autumn Version */
                .fog-overlay {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(139, 69, 19, 0.1);
                    backdrop-filter: blur(8px);
                    z-index: 100;
                    opacity: 0;
                    transition: opacity 3s ease-in-out;
                    pointer-events: none;
                }}

                /* Autumn Pattern */
                .autumn-pattern {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-image: 
                        radial-gradient(circle at 20% 80%, rgba(255, 140, 0, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(210, 105, 30, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 40% 40%, rgba(139, 69, 19, 0.05) 0%, transparent 50%);
                    z-index: -1;
                    pointer-events: none;
                }}

                /* Main Container */
                .glass-container {{
                    max-width: 900px;
                    margin: 0 auto;
                    padding: 15px;
                    position: relative;
                    z-index: 10;
                }}
                
                /* Header - More Transparent */
                .glass-header {{
                    background: var(--glass-autumn);
                    backdrop-filter: var(--glass-blur);
                    -webkit-backdrop-filter: var(--glass-blur);
                    border: 1px solid var(--glass-border);
                    border-radius: 24px;
                    padding: 30px 25px;
                    margin-bottom: 20px;
                    box-shadow: 
                        var(--glass-shadow),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                    transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                }}
                
                .glass-header:hover {{
                    transform: scale(1.02);
                }}
                
                .glass-header::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, 
                        transparent, 
                        rgba(255, 165, 0, 0.15), 
                        transparent);
                    transition: left 0.6s ease;
                }}
                
                .glass-header:hover::before {{
                    left: 100%;
                }}
                
                .glass-title {{
                    font-size: 36px;
                    font-weight: 800;
                    margin-bottom: 8px;
                    color: var(--text-autumn);
                    letter-spacing: -1px;
                    text-shadow: 0 2px 4px rgba(101, 67, 33, 0.5);
                    transition: transform 0.3s ease;
                }}
                
                .glass-header:hover .glass-title {{
                    transform: scale(1.05);
                }}
                
                .glass-subtitle {{
                    font-size: 16px;
                    color: var(--text-autumn-light);
                    font-weight: 400;
                    text-shadow: 0 1px 2px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }}
                
                .glass-header:hover .glass-subtitle {{
                    transform: scale(1.03);
                }}
                
                /* Stats Grid - More Transparent */
                .glass-stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 12px;
                    margin-bottom: 20px;
                }}
                
                .glass-stat-card {{
                    background: var(--glass-autumn);
                    backdrop-filter: var(--glass-blur);
                    -webkit-backdrop-filter: var(--glass-blur);
                    border: 1px solid var(--glass-border);
                    border-radius: 20px;
                    padding: 20px 15px;
                    text-align: center;
                    box-shadow: 
                        var(--glass-shadow),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                    position: relative;
                    overflow: hidden;
                }}
                
                .glass-stat-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, 
                        transparent, 
                        rgba(255, 165, 0, 0.15), 
                        transparent);
                    transition: left 0.6s ease;
                }}
                
                .glass-stat-card:hover::before {{
                    left: 100%;
                }}
                
                .glass-stat-card:hover {{
                    transform: translateY(-6px) scale(1.05);
                    box-shadow: 
                        var(--glass-shadow-elevated),
                        inset 0 1px 0 rgba(255, 255, 255, 0.15);
                }}
                
                .glass-stat-value {{
                    font-size: 32px;
                    font-weight: 800;
                    margin-bottom: 4px;
                    color: var(--text-autumn);
                    text-shadow: 0 2px 4px rgba(101, 67, 33, 0.5);
                    letter-spacing: -0.5px;
                    transition: transform 0.3s ease;
                }}
                
                .glass-stat-card:hover .glass-stat-value {{
                    transform: scale(1.1);
                }}
                
                .glass-stat-label {{
                    font-size: 14px;
                    color: var(--text-autumn-light);
                    font-weight: 500;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    text-shadow: 0 1px 2px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }}
                
                .glass-stat-card:hover .glass-stat-label {{
                    transform: scale(1.05);
                }}
                
                /* Financial Stats - More Transparent */
                .glass-financial-stats {{
                    background: linear-gradient(135deg, 
                        rgba(210, 105, 30, 0.18),
                        rgba(255, 140, 0, 0.16),
                        rgba(255, 165, 0, 0.14),
                        rgba(255, 215, 0, 0.12)
                    );
                    backdrop-filter: blur(40px);
                    border-radius: 22px;
                    padding: 25px 20px;
                    margin-bottom: 20px;
                    box-shadow: 
                        0 15px 40px rgba(210, 105, 30, 0.15),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    color: var(--text-autumn);
                    position: relative;
                    overflow: hidden;
                    border: 1px solid rgba(255, 165, 0, 0.25);
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                }}
                
                .glass-financial-stats:hover {{
                    transform: translateY(-4px) scale(1.02);
                    box-shadow: 
                        0 20px 50px rgba(210, 105, 30, 0.2),
                        inset 0 1px 0 rgba(255, 255, 255, 0.15);
                }}
                
                .glass-financial-stats::before {{
                    content: '';
                    position: absolute;
                    top: -50%;
                    left: -50%;
                    width: 200%;
                    height: 200%;
                    background: radial-gradient(circle, 
                        rgba(255, 255, 255, 0.2) 0%, 
                        transparent 70%);
                    animation: goldRotate 15s infinite linear;
                    opacity: 0.3;
                }}
                
                .glass-financial-stats::after {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, 
                        transparent, 
                        rgba(255, 255, 255, 0.3), 
                        transparent);
                    transition: left 0.8s ease;
                }}
                
                .glass-financial-stats:hover::after {{
                    left: 100%;
                }}
                
                @keyframes goldRotate {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                
                .glass-financial-title {{
                    font-size: 26px;
                    font-weight: 800;
                    margin-bottom: 20px;
                    text-align: center;
                    position: relative;
                    color: var(--text-autumn);
                    text-shadow: 0 2px 8px rgba(101, 67, 33, 0.5);
                    letter-spacing: -0.5px;
                    transition: transform 0.3s ease;
                    z-index: 2;
                }}
                
                .glass-financial-stats:hover .glass-financial-title {{
                    transform: scale(1.05);
                }}
                
                .glass-financial-grid {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 15px;
                    position: relative;
                    z-index: 2;
                }}
                
                .glass-financial-item {{
                    text-align: center;
                    background: rgba(255, 253, 208, 0.15);
                    backdrop-filter: blur(20px);
                    border-radius: 18px;
                    padding: 20px 15px;
                    border: 1px solid rgba(255, 215, 0, 0.25);
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                    position: relative;
                    overflow: hidden;
                    box-shadow: 0 6px 20px rgba(101, 67, 33, 0.1);
                }}
                
                .glass-financial-item::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, 
                        transparent, 
                        rgba(255, 255, 255, 0.3), 
                        transparent);
                    transition: left 0.6s ease;
                }}
                
                .glass-financial-item:hover::before {{
                    left: 100%;
                }}
                
                .glass-financial-item:hover {{
                    transform: translateY(-6px) scale(1.06);
                    background: rgba(255, 253, 208, 0.2);
                    box-shadow: 0 12px 30px rgba(210, 105, 30, 0.2);
                }}
                
                .glass-financial-amount {{
                    font-size: 34px;
                    font-weight: 900;
                    margin-bottom: 10px;
                    color: var(--text-autumn);
                    text-shadow: 0 2px 6px rgba(101, 67, 33, 0.5);
                    letter-spacing: -1px;
                    transition: transform 0.3s ease;
                }}
                
                .glass-financial-item:hover .glass-financial-amount {{
                    transform: scale(1.12);
                }}
                
                .glass-financial-label {{
                    font-size: 14px;
                    color: var(--text-autumn);
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.8px;
                    text-shadow: 0 1px 2px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }}
                
                .glass-financial-item:hover .glass-financial-label {{
                    transform: scale(1.08);
                }}
                
                /* Progress Section - More Transparent */
                .glass-progress-section {{
                    background: var(--glass-autumn);
                    backdrop-filter: var(--glass-blur);
                    -webkit-backdrop-filter: var(--glass-blur);
                    border: 1px solid var(--glass-border);
                    border-radius: 20px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 
                        var(--glass-shadow),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    transition: transform 0.3s ease;
                }}
                
                .glass-progress-section:hover {{
                    transform: scale(1.02);
                }}
                
                .glass-progress-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }}
                
                .glass-progress-title {{
                    font-size: 20px;
                    font-weight: 700;
                    color: var(--text-autumn);
                    text-shadow: 0 1px 2px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }}
                
                .glass-progress-section:hover .glass-progress-title {{
                    transform: scale(1.05);
                }}
                
                .glass-progress-percent {{
                    font-size: 20px;
                    font-weight: 700;
                    color: var(--text-autumn);
                    text-shadow: 0 1px 2px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }}
                
                .glass-progress-section:hover .glass-progress-percent {{
                    transform: scale(1.05);
                }}
                
                .glass-progress-bar {{
                    background: rgba(255, 253, 208, 0.1);
                    border-radius: 12px;
                    height: 10px;
                    overflow: hidden;
                    position: relative;
                }}
                
                .glass-progress-fill {{
                    background: linear-gradient(90deg, #d2691e, #ff8c00, #ffaa00);
                    height: 100%;
                    border-radius: 12px;
                    transition: width 1.5s cubic-bezier(0.4, 0, 0.2, 1);
                    position: relative;
                    box-shadow: 0 0 15px rgba(210, 105, 30, 0.3);
                }}
                
                .glass-progress-fill::after {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, 
                        transparent, 
                        rgba(255, 255, 255, 0.6), 
                        transparent);
                    animation: glassShine 2s infinite;
                }}
                
                @keyframes glassShine {{
                    0% {{ left: -100%; }}
                    100% {{ left: 100%; }}
                }}
                
                /* Accounts Section */
                .glass-accounts-section {{
                    margin-bottom: 25px;
                }}
                
                .glass-section-title {{
                    font-size: 28px;
                    font-weight: 700;
                    margin-bottom: 18px;
                    color: var(--text-autumn);
                    letter-spacing: -0.5px;
                    text-align: center;
                    text-shadow: 0 2px 4px rgba(101, 67, 33, 0.5);
                    transition: transform 0.3s ease;
                }}
                
                .glass-accounts-section:hover .glass-section-title {{
                    transform: scale(1.05);
                }}
                
                .glass-accounts-grid {{
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }}
                
                /* Account Cards - More Transparent */
                .account-glass-card {{
                    background: var(--glass-autumn);
                    backdrop-filter: var(--glass-blur);
                    -webkit-backdrop-filter: var(--glass-blur);
                    border: 1px solid var(--glass-border);
                    border-radius: 18px;
                    padding: 18px;
                    box-shadow: 
                        var(--glass-shadow),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                    position: relative;
                    overflow: hidden;
                }}
                
                .account-glass-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, 
                        transparent, 
                        rgba(255, 165, 0, 0.15), 
                        transparent);
                    transition: left 0.6s ease;
                }}
                
                .account-glass-card:hover::before {{
                    left: 100%;
                }}
                
                .account-glass-card:hover {{
                    transform: translateY(-3px) scale(1.02);
                    box-shadow: 
                        var(--glass-shadow-elevated),
                        inset 0 1px 0 rgba(255, 255, 255, 0.15);
                }}
                
                .account-glass-header {{
                    display: flex;
                    align-items: center;
                    margin-bottom: 15px;
                    gap: 12px;
                }}
                
                .account-glass-avatar {{
                    width: 44px;
                    height: 44px;
                    background: rgba(255, 253, 208, 0.15);
                    border-radius: 14px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                    color: var(--text-autumn);
                    box-shadow: 0 4px 12px rgba(101, 67, 33, 0.1);
                    backdrop-filter: blur(10px);
                    transition: transform 0.3s ease;
                }}
                
                .account-glass-card:hover .account-glass-avatar {{
                    transform: scale(1.1);
                }}
                
                .account-glass-info {{
                    flex: 1;
                }}
                
                .account-username {{
                    font-size: 18px;
                    font-weight: 600;
                    color: var(--text-autumn);
                    margin-bottom: 3px;
                    text-shadow: 0 1px 2px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }}
                
                .account-glass-card:hover .account-username {{
                    transform: scale(1.05);
                }}
                
                .account-user-id {{
                    font-size: 14px;
                    color: var(--text-autumn-light);
                    font-weight: 400;
                    text-shadow: 0 1px 1px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }}
                
                .account-glass-card:hover .account-user-id {{
                    transform: scale(1.03);
                }}
                
                .premium-glass-badge {{
                    background: linear-gradient(135deg, #d2691e, #ff8c00);
                    color: var(--text-autumn);
                    padding: 6px 12px;
                    border-radius: 14px;
                    font-size: 12px;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    box-shadow: 0 4px 15px rgba(210, 105, 30, 0.2);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 215, 0, 0.25);
                    transition: transform 0.3s ease;
                }}
                
                .account-glass-card:hover .premium-glass-badge {{
                    transform: scale(1.1);
                }}
                
                .badge-icon {{
                    font-size: 12px;
                }}
                
                .account-glass-stats {{
                    display: flex;
                    align-items: center;
                    background: rgba(255, 253, 208, 0.1);
                    border-radius: 14px;
                    padding: 12px;
                    backdrop-filter: blur(10px);
                }}
                
                .account-stat-item {{
                    flex: 1;
                    text-align: center;
                }}
                
                .stat-icon {{
                    font-size: 18px;
                    margin-bottom: 4px;
                    opacity: 0.9;
                    filter: drop-shadow(0 1px 1px rgba(101, 67, 33, 0.3));
                    transition: transform 0.3s ease;
                }}
                
                .account-glass-card:hover .stat-icon {{
                    transform: scale(1.2);
                }}
                
                .stat-value {{
                    font-size: 20px;
                    font-weight: 700;
                    color: var(--text-autumn);
                    margin-bottom: 2px;
                    text-shadow: 0 1px 2px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }}
                
                .account-glass-card:hover .stat-value {{
                    transform: scale(1.1);
                }}
                
                .stat-label {{
                    font-size: 12px;
                    color: var(--text-autumn-light);
                    font-weight: 500;
                    text-shadow: 0 1px 1px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }}
                
                .account-glass-card:hover .stat-label {{
                    transform: scale(1.05);
                }}
                
                .account-stat-divider {{
                    width: 1px;
                    height: 28px;
                    background: var(--glass-border);
                    margin: 0 12px;
                }}
                
                /* Timestamp */
                .glass-timestamp {{
                    text-align: center;
                    color: var(--text-autumn-light);
                    font-size: 13px;
                    padding: 18px;
                    font-style: italic;
                    text-shadow: 0 1px 1px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }}
                
                .glass-timestamp:hover {{
                    transform: scale(1.05);
                }}
                
                /* Animations */
                @keyframes glassSlideUp {{
                    from {{
                        opacity: 0;
                        transform: translateY(40px) scale(0.95);
                    }}
                    to {{
                        opacity: 1;
                        transform: translateY(0) scale(1);
                    }}
                }}
                
                .glass-animate {{
                    animation: glassSlideUp 0.8s cubic-bezier(0.4, 0, 0.2, 1) both;
                }}
                
                /* Responsive */
                @media (max-width: 768px) {{
                    .glass-stats-grid {{
                        grid-template-columns: repeat(2, 1fr);
                    }}
                    
                    .glass-financial-grid {{
                        grid-template-columns: 1fr;
                        gap: 15px;
                    }}
                    
                    .glass-container {{
                        padding: 12px;
                    }}
                    
                    .glass-header {{
                        padding: 25px 20px;
                    }}
                    
                    .glass-title {{
                        font-size: 28px;
                    }}
                    
                    .account-glass-header {{
                        flex-direction: column;
                        text-align: center;
                        gap: 10px;
                    }}
                    
                    .account-glass-stats {{
                        flex-direction: column;
                        gap: 10px;
                    }}
                    
                    .account-stat-divider {{
                        width: 100%;
                        height: 1px;
                        margin: 6px 0;
                    }}
                }}
            </style>
        </head>
        <body>
            <!-- Autumn Parallax Layers -->
            <section class="layers">
                <div class="layers__container">
                    <div class="layers__item layer-1"></div>
                    <div class="layers__item layer-2"></div>
                    <div class="layers__item layer-3"></div>
                    <div class="layers__item layer-4">
                        <canvas class="rain"></canvas>
                    </div>
                    <div class="layers__item layer-5"></div>
                    <div class="layers__item layer-6"></div>
                </div>
            </section>

            <!-- Autumn Leaves -->
            <div class="autumn-leaves">
                <div class="leaf leaf-1"></div>
                <div class="leaf leaf-2"></div>
                <div class="leaf leaf-3"></div>
                <div class="leaf leaf-4"></div>
                <div class="leaf leaf-5"></div>
                <div class="leaf leaf-6"></div>
                <div class="leaf leaf-7"></div>
                <div class="leaf leaf-8"></div>
                <div class="leaf leaf-9"></div>
                <div class="leaf leaf-10"></div>
                <div class="leaf leaf-11"></div>
                <div class="leaf leaf-12"></div>
                <div class="leaf leaf-13"></div>
                <div class="leaf leaf-14"></div>
                <div class="leaf leaf-15"></div>
                <div class="leaf leaf-16"></div>
                <div class="leaf leaf-17"></div>
                <div class="leaf leaf-18"></div>
                <div class="leaf leaf-19"></div>
                <div class="leaf leaf-20"></div>
            </div>

            <!-- Light Overlay -->
            <div class="light-overlay"></div>

            <!-- Fog Effect -->
            <div class="fog-overlay" id="fogOverlay"></div>

            <!-- Autumn Pattern -->
            <div class="autumn-pattern"></div>
            
            <!-- Main Content -->
            <div class="glass-container">
                <!-- Header -->
                <div class="glass-header glass-animate" style="animation-delay: 0.1s">
                    <h1 class="glass-title">🍂 Celestial Checker</h1>
                    <div class="glass-subtitle">Детальная статистика проверки аккаунтов</div>
                </div>
                
                <!-- Stats Grid -->
                <div class="glass-stats-grid">
                    <div class="glass-stat-card glass-animate" style="animation-delay: 0.2s">
                        <div class="glass-stat-value">{stats_data['total_accounts']}</div>
                        <div class="glass-stat-label">Всего</div>
                    </div>
                    <div class="glass-stat-card glass-animate" style="animation-delay: 0.3s">
                        <div class="glass-stat-value">{stats_data['valid_accounts']}</div>
                        <div class="glass-stat-label">Валидных</div>
                    </div>
                    <div class="glass-stat-card glass-animate" style="animation-delay: 0.4s">
                        <div class="glass-stat-value">{stats_data['invalid_accounts']}</div>
                        <div class="glass-stat-label">Невалидных</div>
                    </div>
                    <div class="glass-stat-card glass-animate" style="animation-delay: 0.5s">
                        <div class="glass-stat-value">{stats_data['premium_count']}</div>
                        <div class="glass-stat-label">Premium</div>
                    </div>
                </div>
                
                <!-- Financial Stats -->
                <div class="glass-financial-stats glass-animate" style="animation-delay: 0.6s">
                    <h2 class="glass-financial-title">💰 ФИНАНСОВАЯ СТАТИСТИКА</h2>
                    <div class="glass-financial-grid">
                        <div class="glass-financial-item">
                            <div class="glass-financial-amount">{stats_data['total_robux']:,}</div>
                            <div class="glass-financial-label">Всего Robux</div>
                        </div>
                        <div class="glass-financial-item">
                            <div class="glass-financial-amount">{stats_data['total_donate']:,}</div>
                            <div class="glass-financial-label">AllTimeDonate</div>
                        </div>
                        <div class="glass-financial-item">
                            <div class="glass-financial-amount">{stats_data['total_brainrot_spent']:,}</div>
                            <div class="glass-financial-label">Steal A Brainrot</div>
                        </div>
                    </div>
                </div>
                
                <!-- Progress -->
                <div class="glass-progress-section glass-animate" style="animation-delay: 0.7s">
                    <div class="glass-progress-header">
                        <div class="glass-progress-title">Успешность проверки</div>
                        <div class="glass-progress-percent">{stats_data['success_rate']}%</div>
                    </div>
                    <div class="glass-progress-bar">
                        <div class="glass-progress-fill" style="width: 0%" data-target="{stats_data['success_rate']}%"></div>
                    </div>
                </div>
                
                <!-- Accounts -->
                <div class="glass-accounts-section">
                    <h2 class="glass-section-title glass-animate" style="animation-delay: 0.8s">👥 Аккаунты</h2>
                    <div class="glass-accounts-grid">
                        {accounts_html}
                    </div>
                </div>
                
                <!-- Timestamp -->
                <div class="glass-timestamp glass-animate" style="animation-delay: 1s">
                    Статистика создана: {datetime.fromisoformat(stats_data['timestamp']).strftime('%d.%m.%Y %H:%M:%S')}
                </div>
            </div>
            
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    // Parallax Effect - Very subtle
                    const layersContainer = document.querySelector('.layers__container');
                    
                    function updateParallax(e) {{
                        const moveX = (e.clientX - window.innerWidth / 2) * 0.0001;
                        const moveY = (e.clientY - window.innerHeight / 2) * 0.0001;
                        
                        document.documentElement.style.setProperty('--move-x', moveX + 'rad');
                        document.documentElement.style.setProperty('--move-y', moveY + 'rad');
                    }}

                    document.addEventListener('mousemove', updateParallax);

                    // Enhanced Autumn Rain Effect
                    const canvas = document.querySelector('.rain');
                    if (!canvas) {{
                        console.log('Canvas not found');
                        return;
                    }}
                    
                    const ctx = canvas.getContext('2d');
                    let width = canvas.width = window.innerWidth;
                    let height = canvas.height = window.innerHeight;

                    class AutumnDrop {{
                        constructor() {{
                            this.reset();
                            this.z = Math.random() * 0.5 + 0.5;
                        }}
                        
                        reset() {{
                            this.x = Math.random() * width;
                            this.y = Math.random() * -height;
                            this.speed = Math.random() * 8 + 4;
                            this.length = Math.random() * 15 + 8;
                            this.opacity = Math.random() * 0.4 + 0.3;
                            this.wind = (Math.random() - 0.5) * 1.2;
                            this.size = Math.random() * 1.5 + 0.8;
                            // Autumn colors
                            this.color = Math.random() > 0.5 ? '255,140,0' : '210,105,30';
                        }}
                        
                        update() {{
                            this.y += this.speed * this.z;
                            this.x += this.wind * this.z;
                            
                            if (this.y > height) {{
                                this.reset();
                                this.y = -20;
                            }}
                        }}
                        
                        draw() {{
                            // Draw autumn drop
                            ctx.beginPath();
                            ctx.arc(this.x, this.y, this.size * this.z, 0, Math.PI * 2);
                            ctx.fillStyle = 'rgba(' + this.color + ', ' + (this.opacity * this.z) + ')';
                            ctx.fill();
                            
                            // Draw drop tail
                            if (this.z > 0.7) {{
                                ctx.beginPath();
                                ctx.moveTo(this.x, this.y);
                                ctx.lineTo(this.x + this.wind * 3, this.y + this.length * this.z);
                                ctx.strokeStyle = 'rgba(' + this.color + ', ' + (this.opacity * this.z * 0.6) + ')';
                                ctx.lineWidth = 0.6 * this.z;
                                ctx.lineCap = 'round';
                                ctx.stroke();
                            }}
                        }}
                    }}

                    // Enhanced Leaf particle effect
                    class LeafParticle {{
                        constructor(x, y, z) {{
                            this.x = x;
                            this.y = y;
                            this.z = z;
                            this.particles = [];
                            this.life = 1.0;
                            this.createParticles();
                        }}
                        
                        createParticles() {{
                            for (let i = 0; i < 5; i++) {{
                                this.particles.push({{
                                    x: this.x,
                                    y: this.y,
                                    vx: (Math.random() - 0.5) * 4 * this.z,
                                    vy: -Math.random() * 3 * this.z,
                                    life: 1.0,
                                    color: Math.random() > 0.5 ? '255,140,0' : '210,105,30'
                                }});
                            }}
                        }}
                        
                        update() {{
                            this.life -= 0.015;
                            this.particles.forEach(p => {{
                                p.x += p.vx;
                                p.y += p.vy;
                                p.vy += 0.1;
                                p.life -= 0.02;
                            }});
                            this.particles = this.particles.filter(p => p.life > 0);
                            return this.life > 0 && this.particles.length > 0;
                        }}
                        
                        draw() {{
                            this.particles.forEach(p => {{
                                ctx.beginPath();
                                ctx.arc(p.x, p.y, 2 * this.z, 0, Math.PI * 2);
                                ctx.fillStyle = 'rgba(' + p.color + ', ' + (p.life * 0.5) + ')';
                                ctx.fill();
                            }});
                        }}
                    }}

                    const autumnDrops = [];
                    const leafParticles = [];
                    const dropCount = 200;

                    for (let i = 0; i < dropCount; i++) {{
                        autumnDrops.push(new AutumnDrop());
                    }}

                    function animateAutumnRain() {{
                        ctx.clearRect(0, 0, width, height);
                        
                        // Semi-transparent background for motion effect
                        ctx.fillStyle = 'rgba(101, 67, 33, 0.04)';
                        ctx.fillRect(0, 0, width, height);
                        
                        // Update and draw drops
                        autumnDrops.forEach(drop => {{
                            const prevY = drop.y;
                            drop.update();
                            
                            // Check collision with ground - create leaf particles
                            if (prevY < height && drop.y >= height) {{
                                leafParticles.push(new LeafParticle(drop.x, height, drop.z));
                            }}
                            
                            drop.draw();
                        }});
                        
                        // Update and draw leaf particles
                        for (let i = leafParticles.length - 1; i >= 0; i--) {{
                            if (!leafParticles[i].update()) {{
                                leafParticles.splice(i, 1);
                            }} else {{
                                leafParticles[i].draw();
                            }}
                        }}
                        
                        requestAnimationFrame(animateAutumnRain);
                    }}

                    // Start autumn rain animation
                    animateAutumnRain();

                    // Fog Effect
                    const fogOverlay = document.getElementById('fogOverlay');
                    let fogTimer;

                    function startFogEffect() {{
                        fogTimer = setInterval(() => {{
                            // Random fog every 15-25 seconds
                            const delay = Math.random() * 10000 + 15000;
                            setTimeout(() => {{
                                if (fogOverlay) {{
                                    fogOverlay.style.opacity = '0.4';
                                    setTimeout(() => {{
                                        fogOverlay.style.opacity = '0';
                                    }}, 4000);
                                }}
                            }}, delay);
                        }}, 35000); // Check every 35 seconds
                    }}

                    startFogEffect();

                    // Progress bar animation
                    const progressFill = document.querySelector('.glass-progress-fill');
                    if (progressFill) {{
                        const targetWidth = progressFill.getAttribute('data-target');
                        setTimeout(() => {{
                            progressFill.style.width = targetWidth;
                        }}, 800);
                    }}
                    
                    // Stagger animation for account cards
                    const accountCards = document.querySelectorAll('.account-glass-card');
                    accountCards.forEach((card, index) => {{
                        card.style.animation = 'glassSlideUp 0.8s cubic-bezier(0.4, 0, 0.2, 1) ' + (0.9 + index * 0.1) + 's both';
                    }});
                }});

                // Event handlers outside DOMContentLoaded
                window.addEventListener('resize', () => {{
                    const canvas = document.querySelector('.rain');
                    if (canvas) {{
                        canvas.width = window.innerWidth;
                        canvas.height = window.innerHeight;
                    }}
                }});
            </script>
        </body>
        </html>
        """
        return html
    
    def serve_404(self):
        """Отправляет страницу 404"""
        html = """
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Страница не найдена - Celestial Checker</title>
            <style>
                :root {
                    --glass-autumn: rgba(139, 69, 19, 0.18);
                    --glass-border: rgba(210, 105, 30, 0.25);
                    --glass-shadow: 0 8px 32px rgba(101, 67, 33, 0.1);
                    --glass-blur: blur(20px);
                    --text-autumn: rgba(255, 253, 208, 0.95);
                    --text-autumn-light: rgba(255, 253, 208, 0.7);
                }
                
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
                    min-height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    color: var(--text-autumn);
                    padding: 20px;
                    position: relative;
                    overflow: hidden;
                    cursor: default;
                }

                /* Autumn Parallax Layers for 404 */
                .layers {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    z-index: -3;
                    overflow: hidden;
                }

                .layers__container {
                    transform-style: preserve-3d;
                    transform: rotateX(var(--move-y)) rotateY(var(--move-x));
                    will-change: transform;
                    transition: transform 0.3s ease-out;
                    position: relative;
                    width: 100%;
                    height: 100%;
                }

                .layers__item {
                    position: absolute;
                    inset: -5vw;
                    background-size: cover;
                    background-position: center;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .layer-1 {
                    background-image: url('https://img10.joyreactor.cc/pics/post/full/OreGairu-Anime-Isshiki-Iroha-5139586.jpeg');
                    transform: translateZ(-40px) scale(1.2);
                    filter: blur(15px) brightness(0.6) contrast(1.1) sepia(0.3) hue-rotate(-10deg);
                }

                .layer-2 {
                    background-image: url('https://img10.joyreactor.cc/pics/post/full/OreGairu-Anime-Isshiki-Iroha-5139586.jpeg');
                    transform: translateZ(-20px) scale(1.1);
                    filter: blur(8px) brightness(0.7) contrast(1.05) sepia(0.2) hue-rotate(-5deg);
                }

                .layer-3 {
                    transform: translateZ(0px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .layer-4 {
                    transform: translateZ(15px);
                    pointer-events: none;
                }

                /* Autumn Leaves for 404 */
                .autumn-leaves {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                    z-index: -1;
                    opacity: 0.7;
                }

                .leaf {
                    position: absolute;
                    background: linear-gradient(45deg, #ff6b35, #ff8e00, #ffaa00);
                    border-radius: 80% 0 80% 0;
                    opacity: 0.7;
                    animation: fall linear infinite;
                }

                .leaf-1 { width: 25px; height: 25px; animation-duration: 18s; left: 10%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }
                .leaf-2 { width: 20px; height: 20px; animation-duration: 22s; left: 20%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }
                .leaf-3 { width: 30px; height: 30px; animation-duration: 15s; left: 30%; background: linear-gradient(45deg, #ff6b35, #ff8e00); }
                .leaf-4 { width: 22px; height: 22px; animation-duration: 25s; left: 40%; background: linear-gradient(45deg, #ffaa00, #ffc400); }
                .leaf-5 { width: 28px; height: 28px; animation-duration: 20s; left: 50%; background: linear-gradient(45deg, #ff8e00, #ffaa00); }

                @keyframes fall {
                    0% {
                        transform: translateY(-100px) rotate(0deg);
                        opacity: 0;
                    }
                    10% {
                        opacity: 0.7;
                    }
                    90% {
                        opacity: 0.7;
                    }
                    100% {
                        transform: translateY(100vh) rotate(360deg);
                        opacity: 0;
                    }
                }

                /* Light Overlay for 404 */
                .light-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: radial-gradient(circle at 20% 80%, rgba(255, 140, 0, 0.1) 0%, transparent 50%);
                    z-index: -2;
                    pointer-events: none;
                }

                /* Rain Canvas for 404 */
                .rain {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                }

                /* Fog Effect for 404 */
                .fog-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(139, 69, 19, 0.1);
                    backdrop-filter: blur(5px);
                    z-index: 100;
                    opacity: 0;
                    transition: opacity 3s ease-in-out;
                    pointer-events: none;
                }
                
                .glass-container {
                    background: var(--glass-autumn);
                    backdrop-filter: var(--glass-blur);
                    -webkit-backdrop-filter: var(--glass-blur);
                    border: 1px solid var(--glass-border);
                    border-radius: 24px;
                    padding: 60px 40px;
                    box-shadow: 
                        var(--glass-shadow),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    text-align: center;
                    max-width: 500px;
                    width: 100%;
                    transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                    z-index: 10;
                }
                
                .glass-container:hover {
                    transform: scale(1.02);
                }
                
                .glass-icon {
                    font-size: 80px;
                    margin-bottom: 24px;
                    opacity: 0.7;
                    filter: drop-shadow(0 4px 8px rgba(101, 67, 33, 0.3));
                    transition: transform 0.3s ease;
                }
                
                .glass-container:hover .glass-icon {
                    transform: scale(1.1);
                }
                
                .glass-title {
                    font-size: 48px;
                    font-weight: 800;
                    margin-bottom: 16px;
                    color: var(--text-autumn);
                    letter-spacing: -1px;
                    text-shadow: 0 2px 4px rgba(101, 67, 33, 0.5);
                    transition: transform 0.3s ease;
                }
                
                .glass-container:hover .glass-title {
                    transform: scale(1.05);
                }
                
                .glass-subtitle {
                    font-size: 17px;
                    color: var(--text-autumn-light);
                    line-height: 1.4;
                    margin-bottom: 8px;
                    opacity: 0.8;
                    text-shadow: 0 1px 2px rgba(101, 67, 33, 0.3);
                    transition: transform 0.3s ease;
                }
                
                .glass-container:hover .glass-subtitle {
                    transform: scale(1.03);
                }
            </style>
        </head>
        <body>
            <!-- Autumn Parallax Layers for 404 -->
            <section class="layers">
                <div class="layers__container">
                    <div class="layers__item layer-1"></div>
                    <div class="layers__item layer-2"></div>
                    <div class="layers__item layer-3"></div>
                    <div class="layers__item layer-4">
                        <canvas class="rain"></canvas>
                    </div>
                </div>
            </section>

            <!-- Autumn Leaves for 404 -->
            <div class="autumn-leaves">
                <div class="leaf leaf-1"></div>
                <div class="leaf leaf-2"></div>
                <div class="leaf leaf-3"></div>
                <div class="leaf leaf-4"></div>
                <div class="leaf leaf-5"></div>
            </div>

            <!-- Light Overlay for 404 -->
            <div class="light-overlay"></div>

            <!-- Fog Effect for 404 -->
            <div class="fog-overlay" id="fogOverlay"></div>
            
            <div class="glass-container">
                <div class="glass-icon">🍂</div>
                <h1 class="glass-title">Celestial Checker</h1>
                <p class="glass-subtitle">Страница не найдена</p>
                <p class="glass-subtitle">Статистика с указанным ID не существует или была удалена</p>
            </div>

            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    // Parallax Effect for 404 - Very subtle
                    const layersContainer = document.querySelector('.layers__container');
                    
                    function updateParallax(e) {{
                        const moveX = (e.clientX - window.innerWidth / 2) * 0.0001;
                        const moveY = (e.clientY - window.innerHeight / 2) * 0.0001;
                        
                        document.documentElement.style.setProperty('--move-x', moveX + 'rad');
                        document.documentElement.style.setProperty('--move-y', moveY + 'rad');
                    }}

                    document.addEventListener('mousemove', updateParallax);

                    // Enhanced Autumn Rain Effect for 404
                    const canvas = document.querySelector('.rain');
                    if (!canvas) {{
                        console.log('Canvas not found');
                        return;
                    }}
                    
                    const ctx = canvas.getContext('2d');
                    let width = canvas.width = window.innerWidth;
                    let height = canvas.height = window.innerHeight;

                    class AutumnDrop {{
                        constructor() {{
                            this.reset();
                            this.z = Math.random() * 0.5 + 0.5;
                        }}
                        
                        reset() {{
                            this.x = Math.random() * width;
                            this.y = Math.random() * -height;
                            this.speed = Math.random() * 8 + 4;
                            this.length = Math.random() * 15 + 8;
                            this.opacity = Math.random() * 0.4 + 0.3;
                            this.wind = (Math.random() - 0.5) * 1.2;
                            this.size = Math.random() * 1.5 + 0.8;
                            this.color = Math.random() > 0.5 ? '255,140,0' : '210,105,30';
                        }}
                        
                        update() {{
                            this.y += this.speed * this.z;
                            this.x += this.wind * this.z;
                            
                            if (this.y > height) {{
                                this.reset();
                                this.y = -20;
                            }}
                        }}
                        
                        draw() {{
                            ctx.beginPath();
                            ctx.arc(this.x, this.y, this.size * this.z, 0, Math.PI * 2);
                            ctx.fillStyle = 'rgba(' + this.color + ', ' + (this.opacity * this.z) + ')';
                            ctx.fill();
                            
                            if (this.z > 0.7) {{
                                ctx.beginPath();
                                ctx.moveTo(this.x, this.y);
                                ctx.lineTo(this.x + this.wind * 3, this.y + this.length * this.z);
                                ctx.strokeStyle = 'rgba(' + this.color + ', ' + (this.opacity * this.z * 0.6) + ')';
                                ctx.lineWidth = 0.6 * this.z;
                                ctx.lineCap = 'round';
                                ctx.stroke();
                            }}
                        }}
                    }}

                    const autumnDrops = [];
                    const dropCount = 150;

                    for (let i = 0; i < dropCount; i++) {{
                        autumnDrops.push(new AutumnDrop());
                    }}

                    function animateRain() {{
                        ctx.clearRect(0, 0, width, height);
                        ctx.fillStyle = 'rgba(101, 67, 33, 0.04)';
                        ctx.fillRect(0, 0, width, height);
                        
                        autumnDrops.forEach(drop => {{
                            drop.update();
                            drop.draw();
                        }});
                        
                        requestAnimationFrame(animateRain);
                    }}

                    animateRain();

                    // Fog Effect for 404
                    const fogOverlay = document.getElementById('fogOverlay');
                    setTimeout(() => {{
                        if (fogOverlay) {{
                            fogOverlay.style.opacity = '0.4';
                            setTimeout(() => {{
                                fogOverlay.style.opacity = '0';
                            }}, 4000);
                        }}
                    }}, 2000);
                }});

                window.addEventListener('resize', () => {{
                    const canvas = document.querySelector('.rain');
                    if (canvas) {{
                        canvas.width = window.innerWidth;
                        canvas.height = window.innerHeight;
                    }}
                }});
            </script>
        </body>
        </html>
        """
        self.send_response(404)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

def run_web_server():
    """Запускает веб-сервер на PythonAnywhere"""
    # НАСТРОЙКИ ДЛЯ PYTHONANYWHERE
    port = 5000  # PythonAnywhere использует порт 5000 для бесплатных аккаунтов
    
    try:
        server_address = ('', port)
        httpd = HTTPServer(server_address, StatsHandler)
        
        print(f"🚀 Веб-сервер запущен на порту {port}")
        print(f"📊 Статистика доступна по адресу: https://ВАШ_ЛОГИН.pythonanywhere.com/stats/ID_STATISTICS")
        print(f"🍂 Celestial Checker в осеннем стиле готов к работе!")
        
        httpd.serve_forever()
    except OSError as e:
        print(f"❌ Ошибка запуска веб-сервера: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Веб-сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка веб-сервера: {e}")

if __name__ == "__main__":
    run_web_server()