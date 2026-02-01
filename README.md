<div align="center">

# 🤖 MitaHelper

### Мощный бот для управления чатами в Telegram, на русском языке

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-0088cc?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/your_bot)
[![Python](https://img.shields.io/badge/Python-3.9+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

<br>

[🚀 Быстрый старт](#-быстрый-старт) •
[📖 Документация](#-команды) •
[🐳 Docker](#-docker) •
[💬 Поддержка](https://t.me/your_chat)

<br>

<img src="https://raw.githubusercontent.com/github/explore/80688e429a7d4ef2fca1e82350fe8e3517d3494d/topics/telegram/telegram.png" width="100">

</div>

---

<br>

## ✨ Почему MitaHelper?

<table>
<tr>
<td width="50%">

### 🇷🇺 Полностью на русском
Все сообщения, команды и интерфейс на русском языке. Никаких английских вставок!

### ⚙️ Удобная настройка
Панель `/config` в личных сообщениях — все настройки в одном месте через кнопки.

### 🛡️ Продвинутая защита
CAS Anti-Spam, капча, антифлуд, чёрный список, антиканал — полный арсенал защиты.

</td>
<td width="50%">

### 🎨 Мультифильтры
Несколько случайных ответов на одно слово — стикеры, GIF, текст.

### ↩️ Отмена наказаний
Кнопка "Отменить" прямо на сообщении о бане/муте — исправляйте ошибки мгновенно.

### 📊 Простое хранение
JSON база данных — никаких внешних БД, всё хранится локально.

</td>
</tr>
</table>

<br>

---

<br>

## 🌟 Возможности

<details open>
<summary><h3>👮 Модерация</h3></summary>

| Функция | Описание |
|:-------:|----------|
| 🔨 **Бан / Мут / Кик** | С указанием причины и времени |
| ⏱️ **Временные ограничения** | `/tban 1h`, `/mute @user 30m` |
| ↩️ **Кнопка отмены** | На каждом сообщении о наказании |
| 🗑️ **Автоудаление команд** | Чат остаётся чистым |
| ⚠️ **Варны** | Система предупреждений с настраиваемым лимитом |

</details>

<details open>
<summary><h3>🛡️ Защита</h3></summary>

| Функция | Описание |
|:-------:|----------|
| 🌐 **CAS Anti-Spam** | Проверка по глобальной базе спамеров |
| 🔐 **Капча** | Математическая или кнопка для новичков |
| 🌊 **Антифлуд** | Защита от спама сообщениями |
| 📛 **Чёрный список** | Автобан за запрещённые слова |
| 📢 **Антиканал** | Удаление сообщений от каналов |
| 🔒 **Локдаун** | Быстрая блокировка входа в чат |

</details>

<details open>
<summary><h3>📝 Контент</h3></summary>

| Функция | Описание |
|:-------:|----------|
| 👋 **Приветствия** | Кастомные сообщения с кнопками и медиа |
| 📜 **Правила** | Команда `/rules` с форматированием |
| 📌 **Заметки** | Быстрый доступ через `#имя` |
| 🔍 **Фильтры** | Автоответы на ключевые слова |
| 🎲 **Мультифильтры** | Случайный ответ из списка |

</details>

<details>
<summary><h3>📋 Логирование</h3></summary>

| Функция | Описание |
|:-------:|----------|
| 📺 **Канал логов** | Все действия модерации |
| ⚙️ **Настраиваемые события** | Выбирайте, что логировать |
| 💬 **Уведомления в чат** | Информация о наказаниях |

</details>

<br>

---

<br>

## 🚀 Быстрый старт

### 📋 Требования

- 🐍 Python **3.9** или выше
- 🤖 Токен бота от [@BotFather](https://t.me/BotFather)
- 🆔 Ваш Telegram ID — узнать: [@userinfobot](https://t.me/userinfobot)

<br>

### 📦 Способ 1: Стандартная установка

```bash
# 1️⃣ Клонируйте репозиторий
git clone https://github.com/your-username/MitaHelper.git
cd MitaHelper

# 2️⃣ Установите зависимости
pip install -r requirements.txt

# 3️⃣ Создайте и настройте .env
cp .env.example .env
nano .env
```

**Минимальный `.env`:**
```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
OWNER_ID=123456789
```

```bash
# 4️⃣ Запустите бота
python -m MitaHelper
```

<br>

### 🪟 Способ 2: Windows

```cmd
run.bat
```

### 🐧 Способ 3: Linux / macOS

```bash
chmod +x run.sh
./run.sh
```

<br>

---

<br>

## 🐳 Docker

### ⚡ Автоматическая установка (рекомендуется)

```bash
chmod +x docker-install.sh
./docker-install.sh
```

> 📝 Скрипт автоматически установит Docker, запросит токен и запустит бота!

<br>

### 🔧 Ручная установка

```bash
# Создайте .env файл
cat > .env << EOF
BOT_TOKEN=ваш_токен_от_botfather
OWNER_ID=ваш_telegram_id
EOF

# Запустите
docker-compose up -d --build
```

<br>

### 📟 Управление контейнером

| Команда | Описание |
|---------|----------|
| `docker-compose logs -f` | 📜 Просмотр логов |
| `docker-compose restart` | 🔄 Перезапуск |
| `docker-compose down` | ⏹️ Остановка |
| `docker-compose up -d --build` | 🔨 Пересборка |

**Или используйте скрипт:**
```bash
./docker-manage.sh logs      # 📜 Логи
./docker-manage.sh restart   # 🔄 Перезапуск
./docker-manage.sh update    # ⬆️ Обновление
```

<br>

---

<br>

## 📋 Команды

<details open>
<summary><h3>👮 Модерация</h3></summary>

| Команда | Описание | Пример |
|:--------|:---------|:-------|
| `/ban` | 🔨 Забанить пользователя | `/ban @user спам` |
| `/ban 1h` | ⏱️ Временный бан | `/ban @user 1h реклама` |
| `/unban` | ✅ Разбанить | `/unban @user` |
| `/mute` | 🔇 Замутить | `/mute @user` |
| `/mute 1h` | ⏱️ Временный мут | `/mute @user 30m спам` |
| `/unmute` | 🔊 Размутить | `/unmute @user` |
| `/kick` | 👢 Кикнуть | `/kick @user` |
| `/warn` | ⚠️ Выдать варн | `/warn @user нарушение` |
| `/unwarn` | ✅ Снять варн | `/unwarn @user` |
| `/warns` | 📋 Список варнов | `/warns @user` |

</details>

<details>
<summary><h3>👑 Администрирование</h3></summary>

| Команда | Описание |
|:--------|:---------|
| `/promote` | ⬆️ Повысить до админа |
| `/demote` | ⬇️ Понизить админа |
| `/pin` | 📌 Закрепить сообщение |
| `/unpin` | 📍 Открепить сообщение |
| `/adminlist` | 👥 Список админов |

</details>

<details>
<summary><h3>📝 Контент</h3></summary>

| Команда | Описание |
|:--------|:---------|
| `/rules` | 📜 Показать правила |
| `/setrules` | ✏️ Установить правила |
| `/save имя` | 💾 Сохранить заметку |
| `#имя` | 📌 Получить заметку |
| `/notes` | 📋 Список заметок |
| `/filter слово` | 🔍 Создать фильтр |
| `/filters` | 📋 Список фильтров |

</details>

<details>
<summary><h3>👋 Приветствия</h3></summary>

| Команда | Описание |
|:--------|:---------|
| `/welcome` | 📖 Текущие настройки |
| `/welcome on/off` | ⚡ Вкл/выкл приветствия |
| `/setwelcome` | ✏️ Установить текст |
| `/resetwelcome` | 🔄 Сбросить приветствие |

</details>

<details>
<summary><h3>🛡️ Защита</h3></summary>

| Команда | Описание |
|:--------|:---------|
| `/lock` | 🔒 Включить локдаун |
| `/unlock` | 🔓 Выключить локдаун |
| `/captcha on/off` | 🔐 Вкл/выкл капчу |
| `/antiflood` | 🌊 Настройки антифлуда |

</details>

<details>
<summary><h3>⚙️ Настройки</h3></summary>

| Команда | Описание |
|:--------|:---------|
| `/config` | ⚙️ Панель управления (в ЛС) |
| `/addmita` | ➕ Добавить бота в чат |
| `/delmita` | ➖ Удалить бота из чата |

</details>

<br>

---

<br>

## ⚙️ Панель управления

Команда `/config` открывает удобную панель настроек:

```
╔══════════════════════════════════════╗
║     ⚙️ Панель управления ботом      ║
╠══════════════════════════════════════╣
║                                      ║
║  📋 Ваши чаты:                       ║
║  • Мой крутой чат                    ║
║  • Тестовая группа                   ║
║                                      ║
║  [⚙️ Мой крутой чат          ]      ║
║  [⚙️ Тестовая группа         ]      ║
║                                      ║
║  [🔄 Обновить]  [❌ Закрыть]         ║
║                                      ║
╚══════════════════════════════════════╝
```

<br>

### 📂 Разделы настроек

| Раздел | Описание |
|:------:|----------|
| 👋 **Приветствия** | Текст, кнопки, автоудаление, локдаун |
| 🔐 **Капча** | Режим, таймаут, мут новичков |
| 📝 **Фильтры** | Обычные и мультифильтры, автоудаление |
| 📌 **Заметки** | Просмотр, редактирование, кнопки |
| 📜 **Правила** | Текст правил чата |
| ⚠️ **Варны** | Лимит варнов, действие при превышении |
| 🛡 **Антифлуд** | Лимит сообщений, действие |
| 🚫 **Чёрный список** | Запрещённые слова и действие |
| 👥 **Админы бота** | Управление админами бота |
| 🧹 **Сервисные** | Удаление системных сообщений |
| 📋 **Логи** | Канал логов, события |
| 🚫 **Медиа-фильтры** | Ограничение типов медиа |
| 🛡 **CAS Anti-Spam** | Проверка по базе спамеров |
| 📢 **Антиканал** | Удаление сообщений от каналов |

<br>

---

<br>

## 🔧 Конфигурация

### 📝 Переменные окружения

| Переменная | Обязательная | Описание |
|:-----------|:------------:|:---------|
| `BOT_TOKEN` | ✅ | Токен от @BotFather |
| `OWNER_ID` | ✅ | Ваш Telegram ID |
| `BOT_NAME` | ❌ | Имя бота |
| `BOT_USERNAME` | ❌ | Username бота |
| `SUDO_USERS` | ❌ | ID суперпользователей через пробел |
| `DEV_USERS` | ❌ | ID разработчиков через пробел |
| `SUPPORT_CHAT` | ❌ | Username чата поддержки |
| `WORKERS` | ❌ | Количество воркеров (по умолчанию: 8) |

<br>

### 📄 Пример `.env` файла

```env
# ═══════════════════════════════════════
#          🤖 MitaHelper Config
# ═══════════════════════════════════════

# 🔑 Обязательные
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
OWNER_ID=123456789

# ⚙️ Опциональные
BOT_NAME=МойБот
BOT_USERNAME=my_helper_bot
SUDO_USERS=111111111 222222222
SUPPORT_CHAT=my_support_chat
```

<br>

---

<br>

## 📁 Структура проекта

```
MitaHelper/
│
├── 📂 MitaHelper/
│   ├── 📄 __init__.py          # Инициализация бота
│   ├── 📄 __main__.py          # Точка входа
│   ├── 📄 config.py            # Конфигурация
│   │
│   ├── 📂 modules/             # Модули бота
│   │   ├── 👑 admin.py         # Администрирование
│   │   ├── 🔨 bans.py          # Баны, муты, кики
│   │   ├── 👋 welcome.py       # Приветствия
│   │   ├── 📌 notes.py         # Заметки
│   │   ├── 🔍 filters.py       # Фильтры
│   │   ├── 📜 rules.py         # Правила
│   │   ├── ⚠️ warns.py          # Варны
│   │   ├── 🌊 antiflood.py     # Антифлуд
│   │   ├── 📛 blacklist.py     # Чёрный список
│   │   ├── 🔐 captcha.py       # Капча
│   │   ├── 🌐 cas_ban.py       # CAS Anti-Spam
│   │   ├── 📢 antichannel.py   # Антиканал
│   │   ├── 📋 logs.py          # Логирование
│   │   ├── ⚙️ config_panel.py   # Панель /config
│   │   └── 💾 database.py      # Работа с БД
│   │
│   └── 📂 data/                # JSON данные
│
├── 📄 requirements.txt         # Зависимости
├── 🐳 Dockerfile               # Docker образ
├── 🐳 docker-compose.yml       # Docker Compose
├── 📜 docker-install.sh        # Автоустановщик
├── 📜 docker-manage.sh         # Управление Docker
├── 📄 .env.example             # Пример конфигурации
├── 🪟 run.bat                  # Запуск (Windows)
├── 🐧 run.sh                   # Запуск (Linux/macOS)
└── 📖 README.md                # Документация
```

<br>

---

<br>

## 🗄️ Хранение данных

Бот использует JSON файлы — просто и надёжно:

```
📂 MitaHelper/data/
├── 💬 chats.json              # Информация о чатах
├── 👤 users.json              # Информация о пользователях
├── ⚙️ settings.json           # Общие настройки
├── 👋 welcome_settings.json   # Приветствия
├── 🔐 captcha_settings.json   # Капча
├── 📜 rules.json              # Правила
├── 📌 notes.json              # Заметки
├── 🔍 filters.json            # Фильтры
├── 🎲 multi_filters.json      # Мультифильтры
├── ⚠️ warns.json              # Варны
├── 🌊 antiflood.json          # Антифлуд
├── 📛 blacklist.json          # Чёрный список
├── 📋 logs_settings.json      # Настройки логов
├── 🌐 cas_settings.json       # CAS настройки
├── 📢 antichannel.json        # Антиканал
└── 👤 user_settings.json      # Пользовательские настройки
```

<br>

---

<br>

## ❓ FAQ

<details>
<summary><b>🆔 Как узнать свой Telegram ID?</b></summary>

<br>

Напишите любому из этих ботов:
- [@userinfobot](https://t.me/userinfobot)
- [@getmyid_bot](https://t.me/getmyid_bot)

</details>

<details>
<summary><b>🤖 Бот не отвечает на команды</b></summary>

<br>

1. Проверьте, что бот добавлен в группу
2. Убедитесь, что бот — администратор
3. Используйте `/addmita` для активации

</details>

<details>
<summary><b>🔄 Как сбросить все настройки?</b></summary>

<br>

Владелец бота может использовать:
`/config` → **"🐟 Режим рыбки"**

</details>

<details>
<summary><b>💾 Данные не сохраняются после перезапуска (Docker)</b></summary>

<br>

Убедитесь, что volume подключен правильно в `docker-compose.yml`:
```yaml
volumes:
  - ./MitaHelper/data:/app/MitaHelper/data
```

</details>

<details>
<summary><b>⬆️ Как обновить бота?</b></summary>

<br>

```bash
# Остановите бота
docker-compose down

# Получите обновления
git pull

# Перезапустите
docker-compose up -d --build
```

</details>

<br>

---

<br>

## 📝 Лицензия

Этот проект распространяется под лицензией **MIT**.

Подробности в файле [LICENSE](LICENSE).

<br>

---

<br>

## 🙏 Благодарности

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) — основной фреймворк
- [FallenRobot](https://github.com/AnonymousX1025/FallenRobot) — оригинальный бот, на основе которого создан MitaHelper
- Claude Opus 4.5

<br>

---

<br>

<div align="center">

### ⭐ Если проект полезен — поставьте звезду!

<br>

**Сделано с ❤️ для русскоязычного сообщества Telegram**

<br>

[![Telegram Bot](https://img.shields.io/badge/🦊_FoxCloud_Bot-0088cc?style=for-the-badge&logo=telegram)](https://t.me/foxicloudbot)
[![Owner](https://img.shields.io/badge/👤_Владелец-0088cc?style=for-the-badge&logo=telegram)](https://t.me/ghost552)

</div>




