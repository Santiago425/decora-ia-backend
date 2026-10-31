import pytest

from app.core.database import Database
from app.models import FurnitureItem, Redesign, RedesignStatus
from app.patterns.ai.ai_decorators import CachingImageEditor
from app.patterns.ai.ai_provider import ImageData, ImageEditor
from app.patterns.builders.redesign_request_builder import RedesignRequestBuilder, RedesignRequestError
from app.patterns.states.redesign_states import InvalidTransition, RedesignProcess
from app.patterns.strategies.budget_strategies import STRATEGIES, select_budget_strategy
from app.repositories import RoomTypeRepository, StyleRepository

IMAGE = ImageData(b"fake", "image/jpeg")


@pytest.fixture
def catalog():
    with Database().session() as session:
        yield RoomTypeRepository(session).get_by_slug("bedroom"), StyleRepository(session).get_by_slug("nordic")


def builder(catalog):
    room, style = catalog
    return RedesignRequestBuilder("COP").with_photo(IMAGE).for_room(room).in_style(style)


def test_builder_creates_a_complete_request(catalog):
    request = (
        builder(catalog)
        .with_palette(["#AABBCC", "#112233"])
        .with_budget(2_000_000, STRATEGIES["economic"])
        .keeping_structure(True)
        .build()
    )
    assert request.palette == ("#aabbcc", "#112233")
    prompt = request.image_prompt()
    assert "nordic" in prompt and "Keep the room structure" in prompt and "#aabbcc" in prompt
    assert "2,000,000 COP" in request.advice_prompt()


def test_builder_validates_required_parts(catalog):
    room, style = catalog
    with pytest.raises(RedesignRequestError, match="foto"):
        RedesignRequestBuilder("COP").for_room(room).in_style(style).build()
    with pytest.raises(RedesignRequestError, match="estilo"):
        RedesignRequestBuilder("COP").with_photo(IMAGE).for_room(room).in_style(None).build()
    with pytest.raises(RedesignRequestError, match="paleta"):
        builder(catalog).with_palette(["red"]).with_budget(None, STRATEGIES["standard"]).build()


def test_budget_strategy_is_selected_by_amount():
    assert select_budget_strategy(None, 100, 1000).key == "standard"
    assert select_budget_strategy(50, 100, 1000).key == "economic"
    assert select_budget_strategy(500, 100, 1000).key == "standard"
    assert select_budget_strategy(5000, 100, 1000).key == "premium"


def test_budget_strategies_pick_cheap_middle_or_expensive_items():
    items = [FurnitureItem(name=n, price=p) for n, p in (("a", 100), ("b", 300), ("c", 200))]
    catalog = {"sofa": items}
    assert STRATEGIES["economic"].pick(catalog, 5)[0].name == "a"
    assert STRATEGIES["standard"].pick(catalog, 5)[0].name == "c"
    assert STRATEGIES["premium"].pick(catalog, 5)[0].name == "b"


def test_redesign_state_transitions():
    redesign = Redesign(status=RedesignStatus.UPLOADING)
    process = RedesignProcess(redesign)
    with pytest.raises(InvalidTransition):
        process.complete("/x.jpg")
    process.start_processing()
    assert redesign.status == RedesignStatus.PROCESSING
    process.fail("La IA falló")
    assert redesign.status == RedesignStatus.ERROR and redesign.error_message == "La IA falló"
    process.start_processing()
    process.complete("/result.jpg")
    assert redesign.status == RedesignStatus.READY and redesign.result_image_url == "/result.jpg"
    with pytest.raises(InvalidTransition):
        process.fail("late error")


def test_caching_decorator_avoids_repeated_ai_calls():
    class CountingEditor(ImageEditor):
        name = "counting"
        calls = 0

        def edit(self, image, prompt):
            self.calls += 1
            return ImageData(prompt.encode(), "image/png")

    inner = CountingEditor()
    editor = CachingImageEditor(inner, max_entries=2)
    editor.edit(IMAGE, "a")
    editor.edit(IMAGE, "a")
    editor.edit(IMAGE, "b")
    editor.edit(IMAGE, "c")
    editor.edit(IMAGE, "a")
    assert inner.calls == 4


def test_budget_strategy_stays_within_the_budget():
    catalog = {
        "sofa": [FurnitureItem(name="sofa", price=700), FurnitureItem(name="sofa-lux", price=2000)],
        "lamp": [FurnitureItem(name="lamp", price=200), FurnitureItem(name="lamp-lux", price=900)],
        "rug": [FurnitureItem(name="rug", price=500)],
    }
    picks = STRATEGIES["premium"].pick(catalog, 5, budget=1000)
    assert [item.name for item in picks] == ["sofa", "lamp"]
    assert sum(item.price for item in picks) <= 1000
