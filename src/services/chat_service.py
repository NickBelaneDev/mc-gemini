import time
from google import genai
from pydantic import BaseModel
from src.llm.client import MCGeminiLLM


"""Damit wir unsere Minecraft Chats hosten können, brauchen wir einen Backendservice.
Dieser überwacht die Chats und entscheidet, ob ein neuer gestartet wird und ob ein Chat vergessen wird.
Die Chats werden in einem Dictionary gespeichert."""
class SmartGeminiBackend:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.mc_gemini_llm = MCGeminiLLM(self.client)

        # Hier speichern wir: {'SpielerName': {'chat': chat_objekt, 'last_active': zeitstempel}}
        self.sessions = {}

        # Zeit in Sekunden, bis ein Chat vergessen wird (5 Minuten)
        self.TIMEOUT_SECONDS = 300

    def _get_clean_session(self, player_name: str):
        current_time = time.time()

        if player_name in self.sessions:
            last_active = self.sessions[player_name]['last_active']

            if (current_time - last_active) > self.TIMEOUT_SECONDS:
                print(f"Session für {player_name} abgelaufen. Starte neuen Kontext.")
                del self.sessions[player_name]
            else:
                return self.sessions[player_name]['chat']


        if player_name not in self.sessions:
            new_chat = self.mc_gemini_llm.get_chat()
            print(f"Neuer Chat mit {player_name} erstellt!")

            self.sessions[player_name] = {
                'chat': new_chat,
                'last_active': current_time
            }

        return self.sessions[player_name]['chat']

    def chat(self, player_name: str, message: str) -> str:
        """"""
        chat_session = self._get_clean_session(player_name)
        response = chat_session.send_message(message)

        self.sessions[player_name]['last_active'] = time.time()

        return response.text

    def cleanup_memory(self):
        """Clear all inactive chat sessions."""
        current_time = time.time()

        to_delete = [
            player for player, data in self.sessions.items()
            if (current_time - data['last_active']) > self.TIMEOUT_SECONDS
        ]
        for player in to_delete:
            del self.sessions[player]
            print(f"Inaktive Session von {player} bereinigt.")