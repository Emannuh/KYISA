from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import HttpResponse
from .models import NewsArticle, NewsCategory, GalleryAlbum, GalleryImage, Video


def news_list_view(request):
    """Public news listing with category filter and search."""
    articles = NewsArticle.objects.filter(status="published").select_related("category", "author")
    categories = NewsCategory.objects.all()

    # Filters
    category_slug = request.GET.get("category", "")
    search = request.GET.get("q", "")

    if category_slug:
        articles = articles.filter(category__slug=category_slug)
    if search:
        articles = articles.filter(title__icontains=search)

    # Featured / highlights
    featured = articles.filter(is_featured=True).first()
    highlights = articles.filter(is_highlight=True)[:4]

    paginator = Paginator(articles, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "public/news_list.html", {
        "active_page": "news_media",
        "page_obj": page_obj,
        "featured": featured,
        "highlights": highlights,
        "categories": categories,
        "current_category": category_slug,
        "search_query": search,
    })


def news_detail_view(request, slug):
    """Single article detail page."""
    article = get_object_or_404(NewsArticle, slug=slug, status="published")
    related = (
        NewsArticle.objects.filter(status="published", category=article.category)
        .exclude(pk=article.pk)[:3]
    )
    return render(request, "public/news_detail.html", {
        "active_page": "news_media",
        "article": article,
        "related": related,
    })


def gallery_list_view(request):
    """Public gallery albums listing."""
    albums = GalleryAlbum.objects.filter(is_published=True).prefetch_related("images")
    paginator = Paginator(albums, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "public/gallery_list.html", {
        "active_page": "news_media",
        "page_obj": page_obj,
    })


def gallery_detail_view(request, slug):
    """Single album with all photos in a lightbox-style grid."""
    album = get_object_or_404(GalleryAlbum, slug=slug, is_published=True)
    images = album.images.all()
    return render(request, "public/gallery_detail.html", {
        "active_page": "news_media",
        "album": album,
        "images": images,
    })


def photo_download_png(request, pk):
    """Download a gallery photo converted to PNG."""
    from PIL import Image
    import io

    photo = get_object_or_404(GalleryImage, pk=pk)
    img = Image.open(photo.image.path)
    img = img.convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    filename = photo.caption or f"photo_{photo.pk}"
    filename = filename.replace(" ", "_")[:50] + ".png"

    response = HttpResponse(buf.read(), content_type="image/png")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def videos_list_view(request):
    """Public video listing — uploads + YouTube embeds."""
    videos = Video.objects.filter(is_published=True)
    featured_video = videos.filter(is_featured=True).first()

    paginator = Paginator(videos, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "public/videos_list.html", {
        "active_page": "news_media",
        "page_obj": page_obj,
        "featured_video": featured_video,
    })
