"""Server-rendered CUSTOS pages."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.core.config import TEMPLATES_DIR
from backend.services.dashboard import event_detail, finance_cases, growth_cases, overview, recovery_cases, risk_cases

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
def render(request: Request, name: str, **context): return templates.TemplateResponse(request=request, name=name, context={"request": request, **context})

@router.get("/")
@router.get("/")
def landing_page(request: Request): return render(request, "pages/landing.html")

@router.get("/overview", response_class=HTMLResponse)
def overview_page(request: Request): return render(request, "pages/overview.html", page="overview", **overview())
@router.get("/recovery", response_class=HTMLResponse)
def recovery_page(request: Request): return render(request, "pages/recovery.html", page="recovery", cases=recovery_cases())
@router.get("/risk", response_class=HTMLResponse)
def risk_page(request: Request): return render(request, "pages/risk.html", page="risk", cases=risk_cases())
@router.get("/growth", response_class=HTMLResponse)
def growth_page(request: Request): return render(request, "pages/growth.html", page="growth", cases=growth_cases())
@router.get("/finance", response_class=HTMLResponse)
def finance_page(request: Request): return render(request, "pages/finance.html", page="finance", cases=finance_cases())
@router.get("/command", response_class=HTMLResponse)
def command_page(request: Request):
    data = overview(); priorities = [{"label":"Recover eligible failed payments", "value":data["metrics"]["revenue_at_risk"], "href":"/recovery"}, {"label":"Review high-risk transactions", "value":data["metrics"]["risk_exposure"], "href":"/risk"}, {"label":"Investigate finance exceptions", "value":data["metrics"]["finance_exceptions"], "href":"/finance"}, {"label":"Review projected growth opportunities", "value":data["metrics"]["growth_potential"], "href":"/growth"}]
    return render(request, "pages/command.html", page="command", priorities=priorities)
@router.get("/activity", response_class=HTMLResponse)
def activity_page(request: Request): return render(request, "pages/activity.html", page="activity", events=overview()["events"])
@router.get("/policies", response_class=HTMLResponse)
def policies_page(request: Request): return render(request, "pages/policies.html", page="policies")
@router.get("/demo/{event_id}", response_class=HTMLResponse)
def detail_page(request: Request, event_id: str):
    detail = event_detail(event_id)
    return render(request, "pages/event_detail.html", page="recovery", event=detail) if detail else HTMLResponse("Event not found", status_code=404)

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request): return render(request, "pages/login.html")

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request): return render(request, "pages/register.html")
