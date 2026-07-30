from pathlib import Path

FORM = Path('.github/ISSUE_TEMPLATE/accessibility-barrier.yml')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    require(FORM.exists(), f'missing {FORM}')
    text = FORM.read_text(encoding='utf-8')

    required_fragments = [
        'name: الإبلاغ عن عائق في الإتاحة',
        'id: page_url',
        'id: barrier_type',
        'id: observed',
        'id: expected',
        'id: environment',
        'id: impact',
        'id: workaround',
        'id: privacy',
        'required: true',
        'البلاغ عام',
        'معلومات صحية',
        'بيانات تعريفية',
        'قارئ الشاشة',
        'اتجاه RTL',
        'نص مخفي أو مقطوع',
    ]
    for fragment in required_fragments:
        require(fragment in text, f'missing required accessibility feedback contract fragment: {fragment}')

    forbidden = [
        'password',
        'access token',
        'رقم الهوية',
        'رقم الترخيص',
        'ارفق وثيقة',
        'أرفق وثيقة',
    ]
    lowered = text.lower()
    for fragment in forbidden:
        require(fragment.lower() not in lowered, f'unsafe field or request detected: {fragment}')

    required_ids = {'page_url', 'barrier_type', 'observed', 'expected', 'impact'}
    blocks = text.split('\n  - type: ')[1:]
    found_required = set()
    for block in blocks:
        for field_id in required_ids:
            if f'id: {field_id}' in block and 'validations:\n      required: true' in block:
                found_required.add(field_id)
    require(found_required == required_ids, f'required fields are not enforced: {sorted(required_ids - found_required)}')

    privacy_block = next((block for block in blocks if 'id: privacy' in block), '')
    require(privacy_block.count('required: true') >= 2, 'both privacy acknowledgements must be mandatory')

    print('Accessibility feedback form contract passed.')


if __name__ == '__main__':
    main()
