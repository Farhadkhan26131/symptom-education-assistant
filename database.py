import json
import os
from datetime import datetime
import hashlib

class ChatDatabase:
    def __init__(self, db_file="chat_data.json"):
        self.db_file = db_file
        self.data = self.load()
    
    def load(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"conversations": [], "analytics": {"total_queries": 0, "age_groups": {}, "languages": {}}}
        return {"conversations": [], "analytics": {"total_queries": 0, "age_groups": {}, "languages": {}}}
    
    def save(self):
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def add_conversation(self, user_id, messages, age_group, language, query_count):
        conv = {
            "id": len(self.data["conversations"]) + 1,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "messages": messages,
            "age_group": age_group,
            "language": language,
            "query_count": query_count
        }
        self.data["conversations"].append(conv)
        
        # Update analytics
        self.data["analytics"]["total_queries"] += query_count
        self.data["analytics"]["age_groups"][age_group] = self.data["analytics"]["age_groups"].get(age_group, 0) + query_count
        self.data["analytics"]["languages"][language] = self.data["analytics"]["languages"].get(language, 0) + query_count
        
        self.save()
        return conv["id"]
    
    def get_analytics(self):
        return self.data["analytics"]
    
    def get_recent_conversations(self, limit=10):
        return self.data["conversations"][-limit:]
    
    def clear_data(self):
        self.data = {"conversations": [], "analytics": {"total_queries": 0, "age_groups": {}, "languages": {}}}
        self.save()