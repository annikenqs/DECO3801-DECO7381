from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
import json

from .models import Player, Question, Answer

def _ensure_player(user):
    """Create a Player profile for the logged-in user if missing."""
    p, _ = Player.objects.get_or_create(user=user)
    return p

@login_required
@csrf_exempt  
@require_POST

### function that selects the faction 
def select_faction(request):
    """
    Body: {"faction": 0|1|2}
    Minimal: set the faction; reset progress to 0
    """
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    faction = payload.get("faction", 0) # convert to int; return 0 if invalid
    try:
        faction = int(faction)
    except (TypeError, ValueError):
        faction = 0

    player = _ensure_player(request.user) # ensures the player gets a profile
    player.faction = faction # assigns a faction 
    player.current_order = 0 # assigns the player's current question
    player.save(update_fields=["faction", "current_order", "updated_at"]) # updates the player's faction etc

    return JsonResponse({"ok": True, "faction": player.faction})

@login_required
@require_GET
### function that generates questions for the player
def questions_for_player(request):
    """
    Return all questions for the player's faction in defined order.
    Minimal: just dump the 10 questions (id, order, text, options).
    """
    player = _ensure_player(request.user)
    qs = ( # filters questions based on the player's faction - ensures there's 10 of them
        Question.objects
        .filter(faction=player.faction)
        .order_by("order")[:10]
    )

    data = [{ # each question has an id, order, text and options (1 to 3)
        "id": q.id,
        "order": q.order,
        "text": q.text,
        "options": [q.option1, q.option2, q.option3],
    } for q in qs]

    return JsonResponse({"faction": player.faction, "questions": data})

@login_required
@csrf_exempt  
@require_POST

### function that submits the answer
def submit_answer(request):
    """
    Body: {"qid": <int>, "choice": 1..4}
    Minimal: upsert the answer; bump current_order = max(current_order, question.order).
    No faction/order validation.
    """
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    # tries getting the ID and choice
    qid = payload.get("qid")
    choice = payload.get("choice")

    if qid is None or choice is None:
        return HttpResponseBadRequest("Missing qid or choice")

    try:
        qid = int(qid)
        choice = int(choice)
    except (TypeError, ValueError):
        return HttpResponseBadRequest("qid and choice must be integers")

    q = get_object_or_404(Question, id=qid)
    player = _ensure_player(request.user)

    # Upsert answer (no strict validation)
    ans, created = Answer.objects.get_or_create(
        player=player,
        question=q,
        defaults={"choice": choice}
    )

    # if the answer wasn't created, then it creates one and updates the respective fields
    if not created:
        ans.choice = choice
        ans.save(update_fields=["choice", "answered_at"])

    # Bump progress to at least this question's order (optional convenience)
    if player.current_order < q.order:
        player.current_order = q.order
        player.save(update_fields=["current_order", "updated_at"])

    return JsonResponse({"ok": True, "qid": q.id, "choice": choice})

@login_required
@require_GET

# a function that returns the player's answers
def my_answers(request):
    """
    Return the player's current answers as a simple map list.
    Useful for pre-filling UI when resuming.
    """

    # checks if the player exists
    player = _ensure_player(request.user)

    # take in all player-related questions
    rows = Answer.objects.filter(player=player).select_related("question")

    # creates a map containing the question id and corresponding choice
    data = [{"qid": a.question_id, "choice": a.choice} for a in rows]

    # return a json response with the player's current answers in the order that they were made in
    return JsonResponse({"answers": data, "current_order": player.current_order})