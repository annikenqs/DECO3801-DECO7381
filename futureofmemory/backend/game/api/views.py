from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
import json

from ..models import Player, Question, Answer, Faction

def _ensure_player(user):
    """Create a Player profile for the logged-in user if missing."""
    p, _ = Player.objects.get_or_create(user=user)
    return p

@login_required
@csrf_exempt  # keep it simple for early dev; remove later if you want CSRF protection
@require_POST

# selects a faction
def select_faction(request): 
    """
    Body: {"faction": 0|1|2}
    Minimal: set the faction; reset progress to 0. No extra checks.
    """
    try:
        payload = json.loads(request.body or "{}") # checks for "faction": 0/1/2
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    faction = payload.get("faction", 0) # takes in the faction and its corresponding number
    # Convert to int gently; fallback to 0 if invalid
    try:
        faction = int(faction) # converts faction to int; makes a default faction if it isnt possible
    except (TypeError, ValueError):
        faction = 0

    player = _ensure_player(request.user) # calls _ensure_player to get the player object linked to the current user
    player.faction = faction # sets the player's faction to the current value
    player.current_order = 0 # restarts progress
    player.save(update_fields=["faction", "current_order", "updated_at"]) # saves changes

    return JsonResponse({"ok": True, "faction": player.faction})

@login_required
@require_GET
def questions_for_player(request):
    """
    Return all questions for the player's faction in defined order.
    Minimal: just dump the 10 questions (id, order, text, options).
    """
    player = _ensure_player(request.user)
    qs = (
        Question.objects
        .filter(faction=player.faction)
        .order_by("order")[:10]
    )

    data = [{
        "id": q.id,
        "order": q.order,
        "text": q.text,
        "options": [q.option1, q.option2, q.option3],
    } for q in qs]

    return JsonResponse({"faction": player.faction, "questions": data})

@login_required
@csrf_exempt  # keep it simple for early dev
@require_POST
def submit_answer(request):
    """
    Body: {"qid": <int>, "choice": 1..3}
    Minimal: upsert the answer; bump current_order = max(current_order, question.order).
    No faction/order validation.
    """
    try:
        payload = json.loads(request.body or "{}") # expects an answer like {"qid": <int>, "choice": 1..3}
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    qid = payload.get("qid") # gets the question id
    choice = payload.get("choice") # gets the question choice

    if qid is None or choice is None:
        return HttpResponseBadRequest("Missing qid or choice")

    try:
        qid = int(qid)
        choice = int(choice)
    except (TypeError, ValueError):
        return HttpResponseBadRequest("qid and choice must be integers")

    q = get_object_or_404(Question, id=qid) # ensures the referenced question exists
    player = _ensure_player(request.user) # loads/creates the current player

    # Upsert answer (no strict validation)
    ans, created = Answer.objects.get_or_create( # if the player hasn't answered the question, create a new Answer row w the given choice
        player=player,
        question=q,
        defaults={"choice": choice}
    )
    if not created: # if an answer exists, update the existing choice
        ans.choice = choice
        ans.save(update_fields=["choice", "answered_at"])

    # Bump progress to at least this question's order (optional convenience)
    if player.current_order < q.order:
        player.current_order = q.order
        player.save(update_fields=["current_order", "updated_at"])

    return JsonResponse({"ok": True, "qid": q.id, "choice": choice})

@login_required
@require_GET
def my_answers(request):
    """
    Return the player's current answers as a simple map list.
    Useful for pre-filling UI when resuming.
    """
    player = _ensure_player(request.user) # fetches current player object
    rows = Answer.objects.filter(player=player).select_related("question") # queries Answer for all records for the player
    data = [{"qid": a.question_id, "choice": a.choice} for a in rows] # builds a list of dictionaries containing the question id and the player's choice (in numbers)
    return JsonResponse({"answers": data, "current_order": player.current_order})


# returns the next question
@login_required
@require_GET
def next_question(request):
# No further question: {"done": True}
    p = _ensure_player(request.user)
    if p.faction not in [e.value for e in Faction]: # if a faction doesn't exist, ask for it
        return JsonResponse({"need_faction": True})

    next_order = p.current_order + 1 # increments the order, obtaining the next question
    q = Question.objects.filter(faction=p.faction, order=next_order).first() # filter, obtaining the next question
    if not q:
        return JsonResponse({"done": True})

    return JsonResponse({ # return the next question's order, id and options
        "id": q.id,
        "order": q.order,
        "text": q.text,
        "options": [q.option1, q.option2, q.option3],
    })

@login_required
@require_GET
def resume_state(request):
    """
    """
    p = _ensure_player(request.user)
    answered = Answer.objects.filter(
        player=p, question__faction=p.faction
    ).count() if p.faction in [e.value for e in Faction] else 0

    return JsonResponse({
        "faction": p.faction,
        "label": p.get_faction_display() if p.faction in [e.value for e in Faction] else None,
        "current_order": p.current_order,
        "answered": answered,
    })



# from django.shortcuts import render, get_object_or_404
# from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
# from django.contrib.auth.decorators import login_required
# from django.views.decorators.http import require_POST, require_GET
# from django.db.models import Q
# import json

# from .models import Player, Question, Answer, Faction



# def index(request):
#     # just a simple view to test until frontend is ready
#     return HttpResponse("Future of Memory - Backend is ready. ")

# def ping(request):
#     return JsonResponse({"ok": True, "msg": "pong"})


# def ensure_player(user):
#     p, _ = Player.objects.get_or_create(user=user)
#     return p


# @login_required
# @require_POST
# def choose_faction(request):
#     """
#     body: {"faction": 0|1|2}
#     """
#     try:
#         payload = json.loads(request.body or '{}')
#     except json.JSONDecodeError:
#         return HttpResponseBadRequest("Invalid JSON")

#     code = payload.get('faction')
#     valid = [e.value for e in Faction]
#     if code not in valid:
#         return HttpResponseBadRequest("Invalid faction")

#     p = ensure_player(request.user)
#     p.faction = code
#     p.current_order = 0  
#     p.save(update_fields=["faction", "current_order", "updated_at"])

#     return JsonResponse({
#         "ok": True,
#         "faction": p.faction,
#         "label": p.get_faction_display(),
#     })


# @login_required
# @require_GET
# def next_question(request):
# # No further question: {"done": True}
#     p = ensure_player(request.user)
#     if p.faction not in [e.value for e in Faction]:
#         return JsonResponse({"need_faction": True})

#     next_order = p.current_order + 1
#     q = Question.objects.filter(faction=p.faction, order=next_order).first()
#     if not q:
#         return JsonResponse({"done": True})

#     return JsonResponse({
#         "id": q.id,
#         "order": q.order,
#         "text": q.text,
#         "options": [q.option1, q.option2, q.option3, q.option4],
#     })


# @login_required
# @require_POST
# def submit_answer(request, qid: int):
#     try:
#         payload = json.loads(request.body or '{}')
#     except json.JSONDecodeError:
#         return HttpResponseBadRequest("Invalid JSON")

#     choice = payload.get('choice')
#     if choice not in (1, 2, 3, 4):
#         return HttpResponseBadRequest("choice must be 1..4")

#     p = ensure_player(request.user)
#     q = get_object_or_404(Question, id=qid)

#     if q.faction != p.faction:
#         return HttpResponseBadRequest("question not in player's faction")

#     ans, created = Answer.objects.get_or_create(
#         player=p, question=q, defaults={"choice": choice}
#     )
#     if not created:
#         ans.choice = choice
#         ans.save(update_fields=["choice", "answered_at"])

#     if p.current_order < q.order:
#         p.current_order = q.order
#         p.save(update_fields=["current_order", "updated_at"])

#     return JsonResponse({
#         "ok": True,
#         "saved_order": p.current_order,
#     })


# @login_required
# @require_GET
# def resume_state(request):
#     """
#     """
#     p = ensure_player(request.user)
#     answered = Answer.objects.filter(
#         player=p, question__faction=p.faction
#     ).count() if p.faction in [e.value for e in Faction] else 0

#     return JsonResponse({
#         "faction": p.faction,
#         "label": p.get_faction_display() if p.faction in [e.value for e in Faction] else None,
#         "current_order": p.current_order,
#         "answered": answered,
#     })
