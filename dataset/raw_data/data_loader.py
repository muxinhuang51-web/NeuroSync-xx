import json
import os

class DataLoader:
    def __init__(self, raw_data_folder):
        self.raw_data_folder = raw_data_folder

    def _load_data(self, user_index):
        file_path = os.path.join(self.raw_data_folder, f"user_{user_index}.json")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No data file found for user index {user_index}, you need to reset user index.")
        file_path = os.path.join(self.raw_data_folder, f"user_{user_index}.json")
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def get_round_data(self, user_index, round_number):
        data = self._load_data(user_index)
        user_data = data['dialogue']
        if round_number < len(user_data):
            return user_data[round_number]
        else:
            raise IndexError("Round number out of range")

    def get_all_prompts_to_round(self, user_index, round_number):
        data = self._load_data(user_index)
        user_data = data['dialogue']
        if round_number < len(user_data):
            return [f"第{idx + 1}轮: {entry['user_input']}" for idx, entry in enumerate(user_data[:round_number + 1])][::-1]
        else:
            raise IndexError("Round number out of range")


    def get_prompt_or_response(self, user_index, round_number, mode='prompt'):
        data = self._load_data(user_index)
        user_data = data['dialogue']
        if round_number < len(user_data):
            if mode == 'prompt':
                return user_data[round_number]['user_input']
            elif mode == 'response':
                return user_data[round_number]['llm_output']
            else:
                raise ValueError("Mode should be 'prompt' or 'response'")
        else:
            raise IndexError("Round number out of range")

# Example usage:
if __name__ == "__main__":
    raw_data_folder = "/home/wzhangeb/lancet/dataset/raw_data/web_crawler"
    data_loader = DataLoader(raw_data_folder)

    user_index = 1  # Example user index

    # Get data for a specific round
    round_data = data_loader.get_round_data(user_index=user_index, round_number=2)
    print("\n\n Round Data:", round_data)

    # Get all prompts up to a specific round
    all_prompts = data_loader.get_all_prompts_to_round(user_index=user_index, round_number=2)
    print("\n\n All Prompts to Round 2:", all_prompts)

    # Get specific prompt or response for a round
    prompt = data_loader.get_prompt_or_response(user_index=user_index, round_number=2, mode='prompt')
    print("\n\n Prompt for Round 2:", prompt)

    response = data_loader.get_prompt_or_response(user_index=user_index, round_number=2, mode='response')
    print("\n\n Response for Round 2:", response)