from datetime import datetime, timezone


def _find_first_value(data, key_candidates):
    if isinstance(data, dict):
        for key in key_candidates:
            if key in data and data[key] not in (None, "", [], {}):
                return data[key]
        for value in data.values():
            found = _find_first_value(value, key_candidates)
            if found is not None:
                return found
    elif isinstance(data, list):
        for value in data:
            found = _find_first_value(value, key_candidates)
            if found is not None:
                return found
    return None


def _coerce_datetime(raw_value):
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, (int, float)):
        return datetime.fromtimestamp(raw_value if raw_value < 1e11 else raw_value / 1000.0, timezone.utc)
    try:
        if isinstance(raw_value, str) and raw_value.replace('.', '', 1).isdigit():
            return datetime.fromtimestamp(float(raw_value) if float(raw_value) < 1e11 else float(raw_value) / 1000.0, timezone.utc)
    except Exception:
        pass
    try:
        clean_str = str(raw_value).replace('Z', '+00:00').strip()
        if clean_str.endswith('+00:00') or 'T' in clean_str:
            return datetime.fromisoformat(clean_str[:19] + '+00:00')
    except Exception:
        pass
    return None


def normalize_apify_item(item, platform, cutoff_utc):
    if not item or isinstance(item, str):
        return None

    raw_date = (
        _find_first_value(item, ['createTime', 'createdAt', 'timestamp', 'date', 'postedAt', 'postDate'])
        or item.get('createTime')
        or item.get('createdAt')
        or item.get('timestamp')
        or item.get('date')
        or item.get('create_time')
    )
    if isinstance(raw_date, dict):
        raw_date = raw_date.get('timestamp') or raw_date.get('date') or raw_date.get('createdAt')
    is_old = False
    try:
        dt_utc = _coerce_datetime(raw_date)
        if dt_utc is not None and dt_utc < cutoff_utc:
            is_old = True
    except Exception:
        pass

    user = _find_first_value(item, ['authorName', 'author', 'username', 'user', 'ownerName', 'owner', 'name', 'displayName'])
    if isinstance(user, dict):
        user = user.get('name') or user.get('username') or user.get('displayName') or user.get('publicIdentifier') or user.get('uniqueId') or user.get('nickName') or 'Unknown'
    elif isinstance(user, (list, tuple)):
        user = user[0] if user else 'Unknown'
    if not user:
        user = 'Unknown'

    title_raw = _find_first_value(item, ['title', 'text', 'caption', 'description', 'body', 'content', 'contentText', 'postText', 'summary'])
    if isinstance(title_raw, dict):
        title_raw = title_raw.get('text') or title_raw.get('content') or title_raw.get('title') or 'No Title'
    if not title_raw:
        title_raw = 'No Title'
    title = str(title_raw)

    item_id = (
        _find_first_value(item, ['id', 'postId', 'post_id', 'urn'])
        or item.get('id')
        or item.get('postId')
        or item.get('video', {}).get('id')
        or item.get('video_id')
    )
    if not item_id:
        item_id = str(hash(str(item)) % 100000000)

    v_url = (
        _find_first_value(item, ['linkedinUrl', 'url', 'postUrl', 'post_url', 'webUrl', 'shareUrl', 'permalink', 'publicUrl', 'link', 'postLink'])
        or item.get('webVideoUrl')
        or item.get('videoWebUrl')
        or item.get('url')
        or item.get('postUrl')
        or item.get('video_url')
    )
    if not v_url and platform == 'TikTok':
        v_url = f"https://www.tiktok.com/@{user}/video/{item_id}"
    elif not v_url and platform == 'LinkedIn':
        v_url = f"https://www.linkedin.com/feed/update/{item_id}"

    image_url = (
        _find_first_value(item, ['displayUrl', 'imageUrl', 'coverUrl', 'thumbnailUrl', 'mediaUrl', 'image', 'imgUrl'])
        or item.get('displayUrl')
        or item.get('imageUrl')
        or item.get('coverUrl')
        or item.get('video', {}).get('cover')
        or item.get('origin_cover')
        or item.get('videoMeta', {}).get('coverUrl')
    )

    return {
        'url': str(v_url) if v_url else None,
        'title': str(title)[:200],
        'platform': str(platform),
        'user': str(user),
        'date': raw_date,
        'id': str(item_id),
        'image_url': str(image_url) if image_url else None,
        'is_old': is_old,
    }
