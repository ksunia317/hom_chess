import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime


class UserRepository:
    def __init__(self,
                 users_file: str = "users.json",
                 recordings_file: str = "recordings.json",
                 broadcasts_file: str = "broadcasts.json"):
        self.users_file = Path(users_file)
        self.recordings_file = Path(recordings_file)
        self.broadcasts_file = Path(broadcasts_file)
        self._ensure_files_exist()

    def _ensure_files_exist(self):
        for file in [self.users_file, self.recordings_file, self.broadcasts_file]:
            if not file.exists():
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=4)

    def _load_data(self, file_path: Path) -> List[Dict]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading {file_path}: {e}")
            return []

    def _save_data(self, file_path: Path, data: List[Dict]):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving to {file_path}: {e}")

    def get_all_users(self) -> List[Dict]:
        return self._load_data(self.users_file)

    def get_active_users(self) -> List[Dict]:
        return self.get_all_users()

    def get_user_by_id(self, user_id: Union[int, str]) -> Optional[Dict]:
        users = self.get_all_users()
        for user in users:
            uid = user.get('user_id')
            if uid is None:
                continue

            try:
                if int(uid) == int(user_id):
                    return user
            except (TypeError, ValueError):
                continue
        return None

    def add_user(self, user_data: Dict) -> bool:
        if 'user_id' not in user_data:
            print("Error: user_id is missing in user_data")
            return False

        users = self.get_all_users()

        if any(int(u.get('user_id', 0)) == int(user_data['user_id']) for u in users):
            print(f"User {user_data['user_id']} already exists")
            return False

        new_user = {
            'user_id': int(user_data['user_id']),
            'username': user_data.get('username', ''),
            'username_surname': user_data.get('username_surname', ''),
            'username_phone': user_data.get('username_phone', ''),
            'username_email': user_data.get('username_email', ''),
            'username_category': user_data.get('username_category', ''),
            'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        users.append(new_user)
        self._save_data(self.users_file, users)
        print(f"Added new user: {new_user}")
        return True

    def update_user(self, user_id: Union[int, str], update_data: Dict) -> bool:
        users = self.get_all_users()
        updated = False

        for i, user in enumerate(users):
            if int(user.get('user_id', 0)) == int(user_id):
                users[i].update(update_data)
                updated = True
                break

        if updated:
            self._save_data(self.users_file, users)
        return updated

    def get_all_recordings(self) -> List[Dict]:
        return self._load_data(self.recordings_file)

    def get_user_recordings(self, user_id: Union[int, str]) -> List[Dict]:
        recordings = self.get_all_recordings()
        return [
            r for r in recordings
            if int(r.get('user_id', 0)) == int(user_id)
        ]

    def add_recording(self, recording_data: Dict) -> bool:
        recordings = self.get_all_recordings()
        if any(int(r.get('user_id', 0)) == int(recording_data['user_id']) and
               r.get('time') == recording_data.get('time') for r in recordings):
            return False

        recording_data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        recordings.append(recording_data)
        self._save_data(self.recordings_file, recordings)
        return True

    def cancel_recording(self, user_id: Union[int, str], time_slot: str) -> bool:
        recordings = self.get_all_recordings()
        initial_count = len(recordings)

        recordings = [r for r in recordings if not (
                int(r.get('user_id', 0)) == int(user_id) and
                r.get('time') == time_slot
        )]

        if len(recordings) < initial_count:
            self._save_data(self.recordings_file, recordings)
            return True
        return False

    def add_broadcast(self, broadcast_data: Dict) -> bool:
        broadcasts = self._load_data(self.broadcasts_file)

        broadcast_data.update({
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'completed'
        })

        broadcasts.append(broadcast_data)
        self._save_data(self.broadcasts_file, broadcasts)
        return True

    def get_broadcast_history(self) -> List[Dict]:
        return self._load_data(self.broadcasts_file)


class AdminRepository:
    def __init__(self, admins_file: str = "admins.json"):
        self.admins_file = Path(admins_file)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not self.admins_file.exists():
            with open(self.admins_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)

    def _load_data(self) -> List[Dict]:
        try:
            with open(self.admins_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading {self.admins_file}: {e}")
            return []

    def _save_data(self, data: List[Dict]):
        try:
            with open(self.admins_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving to {self.admins_file}: {e}")

    def is_admin(self, user_id: Union[int, str]) -> bool:
        admins = self._load_data()
        return any(int(a.get('admin_id', 0)) == int(user_id) for a in admins)

    def add_admin(self, admin_data: Dict) -> bool:
        if 'admin_id' not in admin_data:
            return False

        admins = self._load_data()

        if any(int(a.get('admin_id', 0)) == int(admin_data['admin_id']) for a in admins):
            return False

        admins.append({
            'admin_id': int(admin_data['admin_id']),
            'username': admin_data.get('username', ''),
            'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'permissions': admin_data.get('permissions', ['broadcast'])
        })

        self._save_data(admins)
        return True

    def remove_admin(self, admin_id: Union[int, str]) -> bool:
        admins = self._load_data()
        initial_count = len(admins)

        admins = [a for a in admins if int(a.get('admin_id', 0)) != int(admin_id)]

        if len(admins) < initial_count:
            self._save_data(admins)
            return True
        return False

    def get_admin_permissions(self, admin_id: Union[int, str]) -> List[str]:
        admins = self._load_data()
        for admin in admins:
            if int(admin.get('admin_id', 0)) == int(admin_id):
                return admin.get('permissions', [])
        return []

    def get_all_recordings_with_users(self) -> List[Dict]:
        recordings = self.get_all_recordings()
        result = []

        for rec in recordings:
            user = self.get_user_by_id(rec['user_id'])
            if user:
                rec.update({
                    'user_name': user.get('username', 'Неизвестно'),
                    'user_phone': user.get('username_phone', 'Не указан')
                })
            else:
                rec.update({
                    'user_name': 'Неизвестно',
                    'user_phone': 'Не указан'
                })
            result.append(rec)

        return result

    def add_broadcast(self, broadcast_data: Dict):
        broadcasts = self._load_data(self.broadcasts_file)
        broadcasts.append(broadcast_data)
        self._save_data(self.broadcasts_file, broadcasts)
