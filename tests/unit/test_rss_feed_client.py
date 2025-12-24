from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from linkurator_core.domain.common.exceptions import InvalidRssFeedError
from linkurator_core.infrastructure.asyncio_impl.http_client import AsyncHttpClient, HttpResponse
from linkurator_core.infrastructure.rss.rss_feed_client import RssFeedClient


@pytest.fixture()
def client() -> RssFeedClient:
    return RssFeedClient()


@pytest.fixture()
def rss_xml() -> str:
    sample_file = Path(__file__).parent / "rss" / "basic_rss_sample.xml"
    with sample_file.open() as f:
        return f.read()


@pytest.fixture()
def atom_xml() -> str:
    sample_file = Path(__file__).parent / "rss" / "basic_atom_sample.xml"
    with sample_file.open() as f:
        return f.read()


@pytest.fixture()
def simple_rss_xml() -> str:
    sample_file = Path(__file__).parent / "rss" / "simple_rss_sample.xml"
    with sample_file.open() as f:
        return f.read()


@pytest.fixture()
def el_pais_xml() -> str:
    sample_file = Path(__file__).parent / "rss" / "el_pais_rss_sample.xml"
    with sample_file.open() as f:
        return f.read()


@pytest.fixture()
def vandal_xml() -> str:
    sample_file = Path(__file__).parent / "rss" / "vandal_rss_sample.xml"
    with sample_file.open() as f:
        return f.read()


def test_parse_feed_info_from_rss_feed(client: RssFeedClient, rss_xml: str) -> None:
    feed_info = client.parse_feed_info(rss_xml)

    assert feed_info.title == "Test RSS Feed"
    assert feed_info.link == "https://example.com"
    assert feed_info.description == "A test RSS feed"
    assert feed_info.language == "en"
    assert feed_info.thumbnail == "https://example.com/image.png"


def test_parse_feed_info_from_atom_feed(client: RssFeedClient, atom_xml: str) -> None:
    feed_info = client.parse_feed_info(atom_xml)

    assert feed_info.title == "Test Atom Feed"
    assert feed_info.link == "https://example.com"
    assert feed_info.description == "A test Atom feed"
    assert feed_info.thumbnail == "https://example.com/logo.png"


@pytest.mark.asyncio()
async def test_get_feed_info_raises_error_for_404() -> None:
    http_client_mock = AsyncMock(spec=AsyncHttpClient)
    http_client_mock.get.return_value = HttpResponse(status=404, text="")

    client = RssFeedClient(http_client=http_client_mock)

    with pytest.raises(InvalidRssFeedError, match="Feed not found"):
        await client.get_feed_info("https://example.com/feed.xml")


def test_parse_feed_info_raises_error_for_invalid_xml(client: RssFeedClient) -> None:
    with pytest.raises(InvalidRssFeedError, match="Failed to parse XML"):
        client.parse_feed_info("not valid xml")


def test_parse_feed_items_from_rss_feed(client: RssFeedClient, rss_xml: str) -> None:
    items = client.parse_feed_items(rss_xml)

    assert len(items) == 2
    assert items[0].title == "First Item"
    assert items[0].link == "https://example.com/item1"
    assert items[0].description == "Description of first item"
    assert items[0].published == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    assert items[1].title == "Second Item"
    assert items[1].link == "https://example.com/item2"
    assert items[1].description == "Description of second item"
    assert items[1].published == datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)


def test_parse_feed_items_from_atom_feed(client: RssFeedClient, atom_xml: str) -> None:
    items = client.parse_feed_items(atom_xml)

    assert len(items) == 2
    assert items[0].title == "First Entry"
    assert items[0].link == "https://example.com/entry1"
    assert items[0].description == "Summary of first entry"
    assert items[0].published == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio()
async def test_get_feed_items_returns_empty_list_for_404() -> None:
    http_client_mock = AsyncMock(spec=AsyncHttpClient)
    http_client_mock.get.return_value = HttpResponse(status=404, text="")

    client = RssFeedClient(http_client=http_client_mock)
    items = await client.get_feed_items("https://example.com/feed.xml")

    assert items == []


def test_parse_el_pais_rss_feed(client: RssFeedClient, el_pais_xml: str) -> None:
    """Test parsing a real-world RSS feed from El Pais newspaper."""
    # Test feed info parsing
    feed_info = client.parse_feed_info(el_pais_xml)

    assert feed_info.title == "EL PAÍS: el periódico global"
    assert feed_info.link == "https://elpais.com"
    assert "Noticias de última hora" in feed_info.description
    assert feed_info.language == "es"
    assert feed_info.thumbnail == "https://ep01.epimg.net/iconos/v1.x/v1.0/promos/promo_og_elpais.png"

    # Test feed items parsing
    items = client.parse_feed_items(el_pais_xml)

    assert len(items) == 6

    # Check first item (Fiscal General podcast - no thumbnail, uses fallback)
    assert items[0].title == "El correo y la nota de prensa, claves para la condena del fiscal general"
    assert "el-correo-y-la-nota-de-prensa-claves-para-la-condena-del-fiscal-general" in items[0].link
    assert items[0].published == datetime(2025, 12, 10, 4, 30, 1, tzinfo=timezone.utc)
    assert "Feed-icon.svg" in items[0].thumbnail

    # Check second item (Alfombra roja - has thumbnail)
    assert items[1].title == "Alfombra roja para el pelo blanco"
    assert "alfombra-roja-para-el-pelo-blanco" in items[1].link
    assert items[1].published == datetime(2025, 12, 10, 4, 30, 1, tzinfo=timezone.utc)
    assert "IKOLXNNREBBO5FNAD4VG4OCVXY.jpg" in items[1].thumbnail

    # Check third item (Video Q&A - nested thumbnail extracted)
    assert items[2].title == "Preguntas y respuestas sobre la sentencia que condena al fiscal general del Estado"
    assert "preguntas-y-respuestas-sobre-la-sentencia-que-condena-al-fiscal-general-del-estado" in items[2].link
    assert items[2].published == datetime(2025, 12, 10, 4, 15, 0, tzinfo=timezone.utc)
    assert "CW5NI2EAFJCURO2D47F6HZZGWI.jpg" in items[2].thumbnail

    # Check fourth item (Economy article)
    assert items[3].title == "La economía española creció un 0,8% en el tercer trimestre"
    assert "economia-espanola-crece-tercer-trimestre" in items[3].link
    assert "PIB español" in items[3].description
    assert items[3].published == datetime(2025, 12, 6, 8, 30, 0, tzinfo=timezone.utc)
    assert "economia-2025-thumb.jpg" in items[3].thumbnail

    # Check fifth item (Climate article)
    assert items[4].title == "El Gobierno anuncia nuevas medidas para combatir el cambio climático"
    assert "gobierno-medidas-cambio-climatico" in items[4].link
    assert items[4].published == datetime(2025, 12, 5, 15, 45, 0, tzinfo=timezone.utc)
    assert "clima-2025-thumb.jpg" in items[4].thumbnail

    # Check sixth item (Sports article)
    assert items[5].title == "La selección española se prepara para el Mundial de 2026"
    assert "seleccion-preparacion-mundial" in items[5].link
    assert items[5].published == datetime(2025, 12, 4, 10, 0, 0, tzinfo=timezone.utc)
    assert "futbol-2025-thumb.jpg" in items[5].thumbnail


def test_parse_vandal_rss_feed(client: RssFeedClient, vandal_xml: str) -> None:
    """Test parsing a real-world RSS feed from Vandal gaming news site."""
    # Test feed info parsing
    feed_info = client.parse_feed_info(vandal_xml)

    assert feed_info.title == "Vandal"
    assert feed_info.link == "https://vandal.elespanol.com"
    assert "Portal especializado en videojuegos" in feed_info.description
    assert feed_info.language == "es-es"
    assert feed_info.thumbnail == "https://www.vandalimg.com/logo.gif"

    # Test feed items parsing
    items = client.parse_feed_items(vandal_xml)

    assert len(items) == 2

    # Check first item (Xbox profit margin article)
    # Note: No standard media:content or enclosure, so uses default feed icon
    assert items[0].title == "Microsoft niega que Xbox tenga como objetivo un margen de beneficio del 30 %"
    assert "microsoft-niega-que-xbox-tenga-como-objetivo-un-margen-de-beneficio-del-30" in items[0].link
    assert items[0].published == datetime(2025, 12, 23, 9, 35, 0, tzinfo=timezone.utc)
    assert items[0].thumbnail == "https://upload.wikimedia.org/wikipedia/en/4/43/Feed-icon.svg"
    assert "La compañía aclara que no ha impuesto ese objetivo" in items[0].description

    # Check second item (Battlefield 6 article)
    assert items[1].title == "Los 25 del 25: Battlefield 6, el regreso del rey de la guerra total"
    assert "battlefield-6-el-regreso-del-rey-de-la-guerra-total" in items[1].link
    assert items[1].published == datetime(2025, 12, 23, 9, 26, 0, tzinfo=timezone.utc)
    assert items[1].thumbnail == "https://upload.wikimedia.org/wikipedia/en/4/43/Feed-icon.svg"
    assert "La destrucción total ha vuelto" in items[1].description


def test_raw_data_includes_root_and_item_tags(client: RssFeedClient, simple_rss_xml: str) -> None:
    """Test that raw_data includes both the root tag and the item tag with correct structure."""
    items = client.parse_feed_items(simple_rss_xml)

    assert len(items) == 2

    item1 = items[0]
    item2 = items[1]

    reparsed_item1 = client.parse_feed_items(item1.raw_data)
    reparsed_item2 = client.parse_feed_items(item2.raw_data)

    assert item1.raw_data == reparsed_item1[0].raw_data
    assert item2.raw_data == reparsed_item2[0].raw_data


def test_raw_data_includes_root_and_entry_tags_for_atom(client: RssFeedClient, atom_xml: str) -> None:
    """Test that raw_data includes both the root feed tag and the entry tag for Atom feeds."""
    items = client.parse_feed_items(atom_xml)

    assert len(items) == 2

    item1 = items[0]
    item2 = items[1]

    reparsed_item1 = client.parse_feed_items(item1.raw_data)
    reparsed_item2 = client.parse_feed_items(item2.raw_data)

    assert item1.raw_data == reparsed_item1[0].raw_data
    assert item2.raw_data == reparsed_item2[0].raw_data
