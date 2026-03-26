scores = {}

def update_score(user, score):
    scores[user] = max(score, scores.get(user, 0))

def get_leaderboard():
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)