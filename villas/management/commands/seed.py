import random
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import quote
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import HostProfile
from villas.models import Villa, VillaPhoto, VillaAmenity, Availability, Wishlist
from bookings.models import Booking
from reviews.models import Review
from payments.models import Payment
from messaging.models import Conversation, Message

User = get_user_model()

# ─── helpers ─────────────────────────────────────────────────────────────────

def P(unsplash_id: str) -> str:
    return f'https://images.unsplash.com/photo-{unsplash_id}?w=800&q=80'

def av(name: str, bg: str = '9BB8B0') -> str:
    return f'https://ui-avatars.com/api/?name={quote(name)}&background={bg}&color=fff&size=64'

PHOTOS = {
    'pool1':    P('1571896349842-33c89424de2d'),
    'rice':     P('1537996194471-e657df975ab4'),
    'pool2':    P('1552733407-5d5c46c3bb3b'),
    'poolDeck': P('1580587771525-4cad66a7af52'),
    'poolRefl': P('1516815231560-8f41ec531527'),
    'outdoor':  P('1582268611958-ebfd161ef9cf'),
    'bedroom':  P('1499793983690-e29da9de2287'),
    'beach':    P('1519046904884-53103b34b206'),
    'cliff':    P('1566073771259-470de1c49b4d'),
    'exterior': P('1558618666-fcd25c85cd64'),
    'living':   P('1619546813926-a78fa6372cd2'),
    'bathoom':  P('1584132967334-10e028bd69f7'),
    'aerial':   P('1543422328-80906e78e59c'),
    'sunset':   P('1535913989690-f90e1c2d4cfa'),
}

# (label_en, label_zh, category, is_highlight)
AMENITY_INFO = {
    'pool':        ('Pool', '泳池', 'outdoor', True),
    'wifi':        ('WiFi', 'WiFi', 'essentials', True),
    'ac':          ('Air Conditioning', '空调', 'essentials', True),
    'kitchen':     ('Kitchen', '厨房', 'kitchen', True),
    'hottub':      ('Hot Tub', '温泉池', 'outdoor', True),
    'bbq':         ('BBQ', '烧烤设施', 'outdoor', False),
    'parking':     ('Parking', '停车场', 'essentials', False),
    'beachaccess': ('Beach Access', '海滩通道', 'outdoor', True),
}

# ─── seed data ───────────────────────────────────────────────────────────────

HOSTS_DATA = [
    {
        'id': 'host-1', 'email': 'wayan@balivilla.dev', 'first_name': 'Wayan', 'last_name': 'Sudana',
        'avatar': 'https://ui-avatars.com/api/?name=Wayan+Sudana&background=1F6B5C&color=fff&size=128',
        'display_name': 'Wayan Sudana', 'hosting_since': 2019, 'response_rate': '98.00',
        'languages': ['Bahasa Indonesia', 'English'],
        'bio': "Born and raised in Ubud, I've spent a decade curating exceptional villa experiences for travellers from around the world. My properties are my passion — every detail has been chosen with care.",
        'total_revenue_idr': '485000000', 'avg_rating': '9.4', 'total_bookings': 87,
    },
    {
        'id': 'host-2', 'email': 'made@balivilla.dev', 'first_name': 'Made', 'last_name': 'Suartika',
        'avatar': 'https://ui-avatars.com/api/?name=Made+Suartika&background=144A3F&color=fff&size=128',
        'display_name': 'Made Suartika', 'hosting_since': 2018, 'response_rate': '99.00',
        'languages': ['Bahasa Indonesia', 'English', 'Japanese'],
        'bio': "After 15 years in hospitality management at five-star Bali resorts, I now focus on my family's private villas. Guests are family — I treat every stay as if you're visiting my home.",
        'total_revenue_idr': '720000000', 'avg_rating': '9.7', 'total_bookings': 124,
    },
    {
        'id': 'host-3', 'email': 'ketut@balivilla.dev', 'first_name': 'Ketut', 'last_name': 'Wijaya',
        'avatar': 'https://ui-avatars.com/api/?name=Ketut+Wijaya&background=9BB8B0&color=fff&size=128',
        'display_name': 'Ketut Wijaya', 'hosting_since': 2020, 'response_rate': '96.00',
        'languages': ['Bahasa Indonesia', 'English'],
        'bio': "Third-generation Balinese architect turned host. Each of my villas is a reflection of traditional Balinese design philosophy — natural materials, open spaces, and harmony with the land.",
        'total_revenue_idr': '312000000', 'avg_rating': '9.2', 'total_bookings': 67,
    },
    {
        'id': 'host-4', 'email': 'nyoman@balivilla.dev', 'first_name': 'Nyoman', 'last_name': 'Artana',
        'avatar': 'https://ui-avatars.com/api/?name=Nyoman+Artana&background=C9A961&color=fff&size=128',
        'display_name': 'Nyoman Artana', 'hosting_since': 2017, 'response_rate': '97.00',
        'languages': ['Bahasa Indonesia', 'English', 'Dutch'],
        'bio': "I manage six villas across Canggu and Seminyak for an international ownership group. Local knowledge, professional service — I'm here to make your Bali trip unforgettable.",
        'total_revenue_idr': '560000000', 'avg_rating': '9.3', 'total_bookings': 203,
    },
    {
        'id': 'host-5', 'email': 'putu@balivilla.dev', 'first_name': 'Putu', 'last_name': 'Dewi',
        'avatar': 'https://ui-avatars.com/api/?name=Putu+Dewi&background=6B8A82&color=fff&size=128',
        'display_name': 'Putu Dewi', 'hosting_since': 2021, 'response_rate': '95.00',
        'languages': ['Bahasa Indonesia', 'English'],
        'bio': "Former travel consultant now living my dream — sharing Bali's beauty from the inside. My villas in Sanur and Nusa Dua are designed for families who want calm, space, and the sea.",
        'total_revenue_idr': '218000000', 'avg_rating': '9.2', 'total_bookings': 89,
    },
]

VILLAS_DATA = [
    {
        'id': 'villa-1', 'slug': 'villa-tjampuhan-ubud', 'hostId': 'host-1',
        'titleEn': 'Villa Tjampuhan Ubud', 'titleZh': '乌布德查潘汉别墅',
        'location': 'Ubud · 5 min to Campuhan Ridge Walk', 'region': 'Ubud',
        'bedrooms': 3, 'beds': 4, 'bathrooms': 3, 'maxGuests': 6, 'highlights': ['peaceful', 'unique'],
        'basePriceIdr': '4500000', 'basePriceCny': '2088', 'rating': '9.4', 'reviewCount': 87,
        'isInstantBook': True, 'badges': ['balivilla_select'],
        'photos': ['rice', 'pool1', 'bedroom', 'living', 'bathoom'],
        'amenities': ['pool', 'wifi', 'ac', 'kitchen', 'hottub'],
        'descriptionEn': "Perched above the Campuhan River valley, this intimate retreat offers sweeping rice terrace views and a heated infinity pool that merges with the jungle horizon at sunset. A private chef can be arranged to prepare traditional Balinese or Chinese dishes in the fully equipped open kitchen.",
        'descriptionZh': "依偎于乌布查潘汉河谷之上，这处宁静的隐居地可俯瞰连绵稻田美景，加热无边泳池与丛林地平线相融。可安排私人厨师，在设备齐全的开放式厨房烹制传统巴厘岛与中式佳肴。",
    },
    {
        'id': 'villa-2', 'slug': 'villa-karang-putih-uluwatu', 'hostId': 'host-2',
        'titleEn': 'Villa Karang Putih Uluwatu', 'titleZh': '乌鲁瓦图白礁悬崖别墅',
        'location': 'Uluwatu · Cliffside · 3 min to Single Fin', 'region': 'Uluwatu',
        'bedrooms': 4, 'beds': 5, 'bathrooms': 4, 'maxGuests': 8, 'highlights': ['stylish', 'unique'],
        'basePriceIdr': '8500000', 'basePriceCny': '3942', 'rating': '9.7', 'reviewCount': 124,
        'isInstantBook': False, 'badges': ['guest_favorite', 'balivilla_select'],
        'photos': ['cliff', 'pool1', 'outdoor', 'bedroom', 'sunset'],
        'amenities': ['pool', 'wifi', 'ac', 'beachaccess', 'bbq'],
        'descriptionEn': "Dramatically positioned on Uluwatu's limestone cliffs, Villa Karang Putih delivers uninterrupted Indian Ocean views from every room. The cantilevered infinity pool hovers 70 metres above the surf, and the rooftop terrace is the finest perch in South Bali to watch the sun disappear.",
        'descriptionZh': "壮观地矗立于乌鲁瓦图石灰岩峭壁之上，白礁别墅每个房间均享有无遮挡的印度洋海景。悬臂式无边泳池悬浮于海浪上方七十米处，屋顶露台是南巴厘岛观赏日落的绝佳之地。",
    },
    {
        'id': 'villa-3', 'slug': 'villa-puri-seminyak', 'hostId': 'host-3',
        'titleEn': 'Villa Puri Seminyak', 'titleZh': '水明漾普里宫殿别墅',
        'location': 'Seminyak · 5 min walk to Seminyak Beach', 'region': 'Seminyak',
        'bedrooms': 5, 'beds': 6, 'bathrooms': 5, 'maxGuests': 10, 'highlights': ['central', 'spacious'],
        'basePriceIdr': '12000000', 'basePriceCny': '5568', 'rating': '9.2', 'reviewCount': 203,
        'isInstantBook': True, 'badges': ['instant_book'],
        'photos': ['poolDeck', 'pool2', 'living', 'bedroom', 'exterior'],
        'amenities': ['pool', 'wifi', 'ac', 'kitchen', 'bbq', 'parking'],
        'descriptionEn': "A modern Balinese palace in the heart of Seminyak, Villa Puri places you moments from the island's finest restaurants, beach clubs, and boutiques. Five ensuite bedrooms surround a 20-metre pool and shaded joglo pavilion that becomes party central by night.",
        'descriptionZh': "坐落于水明漾核心地带的现代巴厘宫殿，普里别墅距岛上最佳餐厅、海滩俱乐部和精品店仅咫尺之遥。五间独立卫浴套房环绕着二十米长泳池和遮阴传统阁楼凉亭，夜晚这里便成为派对中心。",
    },
    {
        'id': 'villa-4', 'slug': 'villa-daun-canggu', 'hostId': 'host-4',
        'titleEn': 'Villa Daun Canggu', 'titleZh': '水流通竹叶艺术别墅',
        'location': 'Canggu · 2 min to Batu Bolong Beach', 'region': 'Canggu',
        'bedrooms': 3, 'beds': 3, 'bathrooms': 3, 'maxGuests': 6, 'highlights': ['stylish', 'central'],
        'basePriceIdr': '5500000', 'basePriceCny': '2552', 'rating': '9.5', 'reviewCount': 156,
        'isInstantBook': True, 'badges': ['guest_favorite', 'instant_book'],
        'photos': ['pool2', 'outdoor', 'bedroom', 'living', 'exterior'],
        'amenities': ['pool', 'wifi', 'ac', 'kitchen', 'bbq'],
        'descriptionEn': "An architect's masterpiece hidden down a quiet Canggu lane, Villa Daun fuses raw concrete and tropical greenery into something genuinely striking. Two minutes on foot puts you at Batu Bolong, the most lively stretch of Canggu beach, yet the villa's high walls make it a world apart.",
        'descriptionZh': "藏在水流通一条宁静小巷里的建筑杰作，竹叶别墅将原始混凝土与热带绿植融为一体，创造出令人印象深刻的视觉奇观。步行两分钟即可到达水流通最热闹的芭杜博朗海滩，而别墅的高墙又将其与外界完全隔绝。",
    },
    {
        'id': 'villa-5', 'slug': 'villa-segara-sanur', 'hostId': 'host-5',
        'titleEn': 'Villa Segara Sanur', 'titleZh': '沙努尔碧海海滨别墅',
        'location': 'Sanur · Beachfront · Direct beach access', 'region': 'Sanur',
        'bedrooms': 4, 'beds': 5, 'bathrooms': 4, 'maxGuests': 8, 'highlights': ['family', 'peaceful'],
        'basePriceIdr': '7200000', 'basePriceCny': '3341', 'rating': '9.3', 'reviewCount': 98,
        'isInstantBook': False, 'badges': ['guest_favorite'],
        'photos': ['beach', 'poolRefl', 'poolDeck', 'bedroom', 'living'],
        'amenities': ['pool', 'wifi', 'ac', 'beachaccess', 'parking'],
        'descriptionEn': "Directly on Sanur's calm reef-protected beach, Villa Segara is the ideal base for families. Step through the garden gate and your toes are in the sand; step back inside to a 14-metre pool, four king bedrooms, and a fully staffed villa team at your service.",
        'descriptionZh': "直接毗邻沙努尔平静礁石保护海滩，碧海别墅是家庭度假的理想选择。穿过花园大门，脚趾便触碰到细沙；返回室内，有十四米长泳池、四间大床套房和全职别墅服务团队恭候。",
    },
    {
        'id': 'villa-6', 'slug': 'villa-bukit-nusa-dua', 'hostId': 'host-1',
        'titleEn': 'Villa Bukit Nusa Dua', 'titleZh': '努沙杜阿布基特豪华别墅',
        'location': 'Nusa Dua · Resort district · Private beach path', 'region': 'Nusa Dua',
        'bedrooms': 6, 'beds': 7, 'bathrooms': 6, 'maxGuests': 12, 'highlights': ['family', 'stylish'],
        'basePriceIdr': '18000000', 'basePriceCny': '8352', 'rating': '9.6', 'reviewCount': 67,
        'isInstantBook': False, 'badges': ['balivilla_select'],
        'photos': ['pool1', 'beach', 'outdoor', 'living', 'bathoom'],
        'amenities': ['pool', 'wifi', 'ac', 'kitchen', 'bbq', 'beachaccess'],
        'descriptionEn': "The grandest property in our Nusa Dua portfolio, Villa Bukit accommodates up to twelve guests in six ocean-view suites surrounding an enormous 25-metre pool. A private path leads directly to the white sand beach, and the dedicated butler coordinates everything from daily breakfast to evening cocktails.",
        'descriptionZh': "努沙杜阿套系中最宏伟的物业，布基特别墅在环绕二十五米大型泳池的六间海景套房中可容纳多达十二位宾客。私人小径直通白沙海滩，专属管家为您协调每日早餐至晚间鸡尾酒的一切安排。",
    },
    {
        'id': 'villa-7', 'slug': 'villa-sawah-ubud', 'hostId': 'host-2',
        'titleEn': 'Villa Sawah Ubud', 'titleZh': '乌布稻田秘境别墅',
        'location': 'Ubud · Rice terrace views · Near Tegallalang', 'region': 'Ubud',
        'bedrooms': 2, 'beds': 2, 'bathrooms': 2, 'maxGuests': 4, 'highlights': ['peaceful', 'unique'],
        'basePriceIdr': '3200000', 'basePriceCny': '1485', 'rating': '9.8', 'reviewCount': 241,
        'isInstantBook': True, 'badges': ['guest_favorite', 'balivilla_select'],
        'photos': ['rice', 'poolRefl', 'bedroom', 'living', 'outdoor'],
        'amenities': ['pool', 'wifi', 'ac', 'hottub'],
        'descriptionEn': "The most-reviewed villa in our Ubud collection, Villa Sawah earns its perfect scores through sheer romance — a plunge pool perched above ancient rice terraces, outdoor rain shower, and beds facing the valley so you wake to green and gold. Ideal for couples celebrating something special.",
        'descriptionZh': "我们乌布精选中评价最多的别墅，稻田别墅凭借纯粹的浪漫氛围赢得满分佳评——俯瞰古老稻田的泳池、户外雨淋浴、面朝山谷的床铺让您在绿意金光中苏醒。最适合情侣庆祝特殊时刻。",
    },
    {
        'id': 'villa-8', 'slug': 'villa-batu-uluwatu', 'hostId': 'host-3',
        'titleEn': 'Villa Batu Uluwatu', 'titleZh': '乌鲁瓦图巨岩海景别墅',
        'location': 'Uluwatu · Ocean views · Near Pura Uluwatu', 'region': 'Uluwatu',
        'bedrooms': 3, 'beds': 3, 'bathrooms': 3, 'maxGuests': 6, 'highlights': ['stylish', 'unique'],
        'basePriceIdr': '6800000', 'basePriceCny': '3155', 'rating': '9.4', 'reviewCount': 112,
        'isInstantBook': True, 'badges': ['instant_book'],
        'photos': ['cliff', 'pool2', 'bedroom', 'sunset', 'outdoor'],
        'amenities': ['pool', 'wifi', 'ac', 'beachaccess'],
        'descriptionEn': "Carved into Uluwatu's volcanic rock, Villa Batu feels like a private fortress on the edge of the world. Three generous suites open onto ocean-facing terraces, the plunge pool glows blue against the limestone, and the kecak fire dance at the nearby temple is visible from your sunlounger.",
        'descriptionZh': "凿入乌鲁瓦图火山岩之中，巨岩别墅犹如世界边缘的私人堡垒。三间宽敞套房朝向海洋露台敞开，水池在石灰岩映衬下泛着蓝光，附近神庙的克差火舞从您的躺椅上便可欣赏。",
    },
    {
        'id': 'villa-9', 'slug': 'villa-pantai-seminyak', 'hostId': 'host-4',
        'titleEn': 'Villa Pantai Seminyak', 'titleZh': '水明漾海滩花园别墅',
        'location': 'Seminyak · 2 min walk to Petitenget Beach', 'region': 'Seminyak',
        'bedrooms': 4, 'beds': 4, 'bathrooms': 4, 'maxGuests': 8, 'highlights': ['central', 'spacious'],
        'basePriceIdr': '9500000', 'basePriceCny': '4407', 'rating': '9.1', 'reviewCount': 178,
        'isInstantBook': False, 'badges': [],
        'photos': ['poolDeck', 'pool1', 'living', 'bedroom', 'exterior'],
        'amenities': ['pool', 'wifi', 'ac', 'kitchen'],
        'descriptionEn': "Set behind a lush garden wall two minutes from Petitenget Beach, Villa Pantai combines Seminyak's unbeatable position with residential privacy. Four bedrooms, a 16-metre pool, and a kitchen stocked daily by the caretaker team make this an easy base for a group holiday.",
        'descriptionZh': "藏在距佩蒂登盖海滩两分钟路程的郁郁葱葱花园墙后，海滩别墅将水明漾无与伦比的地理位置与居家隐私完美结合。四间卧室、十六米长泳池，加上每日由看护团队备货的厨房，让这里成为团体假期的轻松根据地。",
    },
    {
        'id': 'villa-10', 'slug': 'villa-pererenan-canggu', 'hostId': 'host-5',
        'titleEn': 'Villa Pererenan Canggu', 'titleZh': '水流通北部日落别墅',
        'location': 'Canggu · Quiet lane · 10 min to Echo Beach', 'region': 'Canggu',
        'bedrooms': 2, 'beds': 2, 'bathrooms': 2, 'maxGuests': 4, 'highlights': ['stylish', 'central'],
        'basePriceIdr': '3800000', 'basePriceCny': '1763', 'rating': '9.0', 'reviewCount': 89,
        'isInstantBook': True, 'badges': ['instant_book'],
        'photos': ['pool2', 'outdoor', 'bedroom', 'living', 'aerial'],
        'amenities': ['pool', 'wifi', 'ac', 'bbq'],
        'descriptionEn': "A compact, stylish villa in the quieter northern stretch of Canggu, Villa Pererenan is perfect for two couples or a small family who want surf town energy without the crowds. The rooftop BBQ deck catches the famous Canggu sunset every evening.",
        'descriptionZh': "位于水流通北部较安静地带的精巧时尚别墅，北部日落别墅非常适合两对情侣或小家庭，既能感受冲浪小镇的活力，又远离人群喧嚣。屋顶烧烤露台每晚都能欣赏到水流通著名的日落美景。",
    },
    {
        'id': 'villa-11', 'slug': 'villa-sindhu-sanur', 'hostId': 'host-1',
        'titleEn': 'Villa Sindhu Sanur', 'titleZh': '沙努尔辛度家庭度假别墅',
        'location': 'Sanur · 5 min walk to Sindhu Beach', 'region': 'Sanur',
        'bedrooms': 3, 'beds': 4, 'bathrooms': 3, 'maxGuests': 6, 'highlights': ['family', 'peaceful'],
        'basePriceIdr': '5800000', 'basePriceCny': '2691', 'rating': '9.2', 'reviewCount': 143,
        'isInstantBook': False, 'badges': ['guest_favorite'],
        'photos': ['poolRefl', 'beach', 'bedroom', 'living', 'exterior'],
        'amenities': ['pool', 'wifi', 'ac', 'parking'],
        'descriptionEn': "Sanur's calm, shallow seas make it the best part of Bali for families with young children, and Villa Sindhu is precisely calibrated for that market. The pool has a shallow wading section for little ones, there are three spacious bedrooms, and the neighbourhood is safe, walkable, and full of good restaurants.",
        'descriptionZh': "沙努尔平静的浅海使其成为巴厘岛最适合带幼儿家庭的区域，辛度别墅正是为此量身打造。泳池设有儿童浅水区，三间宽敞卧室，周边社区安全宜步行，餐厅众多。",
    },
    {
        'id': 'villa-12', 'slug': 'villa-tanjung-nusa-dua', 'hostId': 'host-2',
        'titleEn': 'Villa Tanjung Nusa Dua', 'titleZh': '努沙杜阿丹宗私人海滩别墅',
        'location': 'Nusa Dua · Resort district · Private beach', 'region': 'Nusa Dua',
        'bedrooms': 5, 'beds': 5, 'bathrooms': 5, 'maxGuests': 10, 'highlights': ['stylish', 'unique'],
        'basePriceIdr': '14500000', 'basePriceCny': '6727', 'rating': '9.5', 'reviewCount': 88,
        'isInstantBook': False, 'badges': ['balivilla_select'],
        'photos': ['beach', 'pool1', 'living', 'bedroom', 'bathoom'],
        'amenities': ['pool', 'wifi', 'ac', 'kitchen', 'beachaccess'],
        'descriptionEn': "Five elegantly appointed suites on a private stretch of white Nusa Dua sand — Villa Tanjung is unapologetically luxurious. The 22-metre pool runs parallel to the sea, daily breakfast is included, and the full-time housekeeper ensures the villa is always immaculate.",
        'descriptionZh': "坐落于努沙杜阿私人白沙海滩上的五间精致套房，丹宗别墅毫不掩饰其奢华本质。二十二米长泳池与大海平行延伸，每日早餐已含，全职管家确保别墅随时一尘不染。",
    },
]

# Guest reviewers — (name, email_slug, avatar_bg)
GUEST_REVIEWERS = [
    ('李明',   'liming',    '1F6B5C'),
    ('Emma K.',  'emmak',     '144A3F'),
    ('王芳',   'wangfang',  '6B8A82'),
    ('张伟',   'zhangwei',  '1F6B5C'),
    ('Thomas B.', 'thomasb', '144A3F'),
    ('陈静',   'chenjing',  '9BB8B0'),
    ('Sarah M.', 'sarahm',  '1F6B5C'),
    ('刘洋',   'liuyang',   '144A3F'),
    ('赵晓丽', 'zhaoxiaoli', '6B8A82'),
    ('黄海',   'huanghai',  '1F6B5C'),
    ('David L.', 'davidl',  '144A3F'),
    ('林敏',   'linmin',    '9BB8B0'),
    ('吴娟',   'wujuan',    '1F6B5C'),
    ('周建国', 'zhoujianguo', '1F6B5C'),
    ('James T.', 'jamest',  '6B8A82'),
]

REVIEWS_DATA = [
    # villa-1 Tjampuhan Ubud
    {'villaId': 'villa-1', 'guestName': '李明', 'rating': '9.6', 'date': '2026-04-15',
     'textEn': "Absolutely magical. The rice terrace views from the infinity pool made every morning feel like a dream. The private chef prepared the most wonderful nasi goreng I've ever tasted.",
     'textZh': "简直令人陶醉。从无边泳池俯瞰稻田美景，每个早晨都如梦似幻。私人厨师烹制的炒饭是我尝过最美味的。",
     'cleanliness': '10', 'accuracy': '9', 'location': '9', 'value': '9'},
    {'villaId': 'villa-1', 'guestName': 'Emma K.', 'rating': '9.4', 'date': '2026-03-28',
     'textEn': "A wonderfully peaceful retreat. Wayan was a superb host — arranged everything from temple visits to a cooking class. The hot tub under the stars on our last night was unforgettable.",
     'textZh': "真正宁静的隐居之所。Wayan是出色的房东，安排了寺庙参观和烹饪课。最后一晚在星空下泡温泉的体验令人难忘。",
     'cleanliness': '10', 'accuracy': '9', 'location': '9', 'value': '9'},
    {'villaId': 'villa-1', 'guestName': '王芳', 'rating': '9.2', 'date': '2026-02-10',
     'textEn': "Came with my husband for our anniversary. The villa team had decorated the pool area with flowers as a surprise — I cried happy tears. Will be back for our 5th anniversary too.",
     'textZh': "和先生来庆祝结婚纪念日。别墅团队用花朵装饰了泳池区域作为惊喜，我感动得流下幸福的眼泪。五周年纪念日我们一定再来。",
     'cleanliness': '9', 'accuracy': '9', 'location': '9', 'value': '8'},
    {'villaId': 'villa-1', 'guestName': 'David L.', 'rating': '9.0', 'date': '2026-01-15',
     'textEn': "A meditative week in Ubud. The rice terraces never get old no matter how many times you look at them. Wayan's team arranged a water purification blessing ceremony at a nearby temple for us.",
     'textZh': "在乌布度过了一周冥思的时光。无论看多少次，稻田美景永不令人厌倦。Wayan的团队为我们在附近寺庙安排了净水祝福仪式。",
     'cleanliness': '9', 'accuracy': '9', 'location': '9', 'value': '9'},
    # villa-2 Karang Putih Uluwatu
    {'villaId': 'villa-2', 'guestName': '张伟', 'rating': '9.8', 'date': '2026-04-20',
     'textEn': "The cliff views are insane. We sat by the infinity pool every evening and just stared at the ocean. Made's recommendations for local warung were spot-on — ate incredibly well all week.",
     'textZh': "悬崖景色令人叹为观止。我们每天傍晚坐在无边泳池旁凝望大海。Made推荐的当地小馆子非常准确，整个星期的饮食都无比美味。",
     'cleanliness': '10', 'accuracy': '10', 'location': '10', 'value': '9'},
    {'villaId': 'villa-2', 'guestName': 'Thomas B.', 'rating': '9.6', 'date': '2026-04-05',
     'textEn': "Brought eight friends for a milestone birthday. The villa handled us all without breaking a sweat. BBQ deck at sunset with the kecak drums in the distance — genuinely one of the best evenings of my life.",
     'textZh': "带着八位朋友来庆祝重要生日。别墅轻松应对我们所有人。日落时分在烧烤露台上，远处传来克差鼓声——真的是我人生中最美好的夜晚之一。",
     'cleanliness': '9', 'accuracy': '10', 'location': '10', 'value': '9'},
    {'villaId': 'villa-2', 'guestName': '吴娟', 'rating': '9.4', 'date': '2026-02-18',
     'textEn': "The cliff views sell it but the villa itself is just as impressive inside. Every bedroom has its own character. Made had Indonesian gin cocktails waiting for us at sunset on the first evening.",
     'textZh': "悬崖景色是卖点，但别墅内部同样令人印象深刻。每间卧室都有其独特个性。第一天傍晚日落时分，Made已准备好印度尼西亚金酒鸡尾酒等候我们。",
     'cleanliness': '10', 'accuracy': '9', 'location': '10', 'value': '9'},
    # villa-3 Puri Seminyak
    {'villaId': 'villa-3', 'guestName': '陈静', 'rating': '9.2', 'date': '2026-03-14',
     'textEn': "Perfect location for a big group — within walking distance of everything Seminyak has to offer. The pool is beautiful and the outdoor joglo is ideal for evening gatherings. Ketut's team kept the villa spotless.",
     'textZh': "大型团体的完美选择，步行即可抵达水明漾所有精彩。泳池美不胜收，户外传统阁楼非常适合晚间聚会。Ketut的团队将别墅保持得一尘不染。",
     'cleanliness': '10', 'accuracy': '9', 'location': '10', 'value': '8'},
    {'villaId': 'villa-3', 'guestName': 'Sarah M.', 'rating': '9.0', 'date': '2026-02-22',
     'textEn': "We had a girls' trip of 9 and this villa was perfect. The bedrooms are all nicely sized with great bathrooms. The only minor thing was the kitchen could use a few more utensils, but overall a fantastic stay.",
     'textZh': "九人女生旅行，这栋别墅完美。每间卧室都宽敞舒适，卫浴设施很棒。唯一小瑕疵是厨房餐具略少，但整体住宿体验非常棒。",
     'cleanliness': '9', 'accuracy': '9', 'location': '10', 'value': '8'},
    {'villaId': 'villa-3', 'guestName': '周建国', 'rating': '9.0', 'date': '2026-03-02',
     'textEn': "Organised a Bali trip for 9 colleagues — all different tastes, all happy. The location is what makes this villa: everything is in walking distance, and Ketut's local knowledge added real depth to our trip.",
     'textZh': "为九位同事组织了一次巴厘岛之旅——口味各异，皆大欢喜。地理位置是这栋别墅的最大卖点：一切步行可达，Ketut的本地知识为我们的旅行增添了真正的深度。",
     'cleanliness': '9', 'accuracy': '9', 'location': '10', 'value': '8'},
    # villa-4 Daun Canggu
    {'villaId': 'villa-4', 'guestName': '刘洋', 'rating': '9.6', 'date': '2026-04-18',
     'textEn': "Surfed Batu Bolong every morning and came back to this masterpiece of a villa. Nyoman sorted a scooter for each of us within an hour of arrival. The concrete-and-plant design is genuinely special.",
     'textZh': "每天清晨在芭杜博朗冲浪，回来后享受这栋杰作别墅。Nyoman在我们抵达一小时内就为每人安排好了摩托车。混凝土与绿植的设计真的很特别。",
     'cleanliness': '10', 'accuracy': '10', 'location': '10', 'value': '9'},
    {'villaId': 'villa-4', 'guestName': '赵晓丽', 'rating': '9.4', 'date': '2026-03-05',
     'textEn': "Canggu energy with true privacy — a rare combination. The BBQ nights were a highlight, and Nyoman's team made sure we always had cold Bintang stocked. Would book this one again without hesitation.",
     'textZh': "水流通的活力与真正的隐私——难得的组合。烧烤之夜是一大亮点，Nyoman的团队确保我们随时有冰镇宾坦啤酒。毫不犹豫会再次预订。",
     'cleanliness': '9', 'accuracy': '9', 'location': '9', 'value': '9'},
    {'villaId': 'villa-4', 'guestName': 'Emma K.', 'rating': '9.4', 'date': '2026-01-30',
     'textEn': "We rented bikes on day one and explored for a week. Villa Daun was the perfect base — cool interior to come back to, excellent WiFi for the freelancers in our group, central to everything good in Canggu.",
     'textZh': "第一天就租了自行车，整整一周四处探索。竹叶别墅是完美的根据地——凉爽的室内环境，优质的WiFi满足我们小组中自由职业者的需求，位于水流通所有精彩的中心位置。",
     'cleanliness': '9', 'accuracy': '9', 'location': '10', 'value': '9'},
    # villa-5 Segara Sanur
    {'villaId': 'villa-5', 'guestName': '黄海', 'rating': '9.4', 'date': '2026-04-10',
     'textEn': "Brought my parents and two kids — everyone was happy, which at my family is a miracle. The direct beach access meant the kids were always occupied, and Sanur's calm water was perfect for my mum who can't swim well.",
     'textZh': "带着父母和两个孩子来，所有人都很开心——在我们家这简直是奇迹。直通海滩的通道让孩子们始终有事可做，沙努尔平静的海水对游泳不好的妈妈来说也很理想。",
     'cleanliness': '9', 'accuracy': '9', 'location': '10', 'value': '9'},
    {'villaId': 'villa-5', 'guestName': 'David L.', 'rating': '9.2', 'date': '2026-03-20',
     'textEn': "A genuinely relaxing week. Sanur is the right part of Bali if you want to escape the tourist frenzy — walkable, local-feeling, and this villa makes it even better with a pool you never want to leave.",
     'textZh': "真正放松的一周。如果你想逃离旅游人潮，沙努尔是巴厘岛的正确选择——宜步行，有生活气息，加上这栋让人流连忘返的泳池别墅，体验更是锦上添花。",
     'cleanliness': '9', 'accuracy': '9', 'location': '9', 'value': '9'},
    {'villaId': 'villa-5', 'guestName': 'James T.', 'rating': '9.4', 'date': '2026-04-16',
     'textEn': "Sanur is the hidden gem of Bali and this villa is its crown jewel. The beachfront location is genuinely steps from the water. Kids loved the sea, adults loved the pool. Putu's team was exceptional.",
     'textZh': "沙努尔是巴厘岛的隐藏宝石，而这栋别墅是其中的明珠。海滨位置真的距海面只有几步之遥。孩子们爱上了大海，大人们爱上了泳池。Putu的团队表现卓越。",
     'cleanliness': '10', 'accuracy': '10', 'location': '10', 'value': '9'},
    # villa-6 Bukit Nusa Dua
    {'villaId': 'villa-6', 'guestName': '林敏', 'rating': '9.8', 'date': '2026-04-25',
     'textEn': "Our company brought the whole team for an offsite — twelve people, five days. The butler, chef, and villa manager made it feel effortless. The 25-metre pool is genuinely the best I've ever swum in.",
     'textZh': "公司带全体团队来进行线下活动——十二人、五天。管家、厨师和别墅经理让一切都如此轻松自然。二十五米长泳池是我游过的最棒的游泳池。",
     'cleanliness': '10', 'accuracy': '10', 'location': '9', 'value': '9'},
    {'villaId': 'villa-6', 'guestName': 'Thomas B.', 'rating': '9.6', 'date': '2026-03-10',
     'textEn': "Second time staying with Wayan's team and the standard never slips. The ocean suite bedrooms are enormous and the butler service is genuinely five-star. Worth every yuan.",
     'textZh': "第二次入住Wayan的团队，品质从未下滑。海景套房卧室宽阔无比，管家服务真正达到五星级水准。每一分钱都物超所值。",
     'cleanliness': '10', 'accuracy': '10', 'location': '9', 'value': '9'},
    # villa-7 Sawah Ubud
    {'villaId': 'villa-7', 'guestName': '吴娟', 'rating': '10.0', 'date': '2026-04-22',
     'textEn': "The best place I have ever stayed. Full stop. We watched the sunrise over the rice terraces from bed through the open window. I've already recommended it to everyone I know.",
     'textZh': "我住过最好的地方。就这样。我们从打开的窗边躺在床上看着日出照耀稻田。我已经向所有认识的人推荐了这里。",
     'cleanliness': '10', 'accuracy': '10', 'location': '10', 'value': '10'},
    {'villaId': 'villa-7', 'guestName': '周建国', 'rating': '9.8', 'date': '2026-04-01',
     'textEn': "Came alone to write and think. The rice terrace view makes it impossible to be stressed. Made had a bag of local fruits and a handwritten welcome note on the table when I arrived. Small things, big impression.",
     'textZh': "独自来此写作思考。稻田美景让人根本无法感到压力。抵达时桌上有Made准备的本地水果和手写欢迎便条。小细节，大感动。",
     'cleanliness': '10', 'accuracy': '10', 'location': '10', 'value': '9'},
    {'villaId': 'villa-7', 'guestName': 'James T.', 'rating': '9.6', 'date': '2026-03-15',
     'textEn': "Honeymooned here. The outdoor rain shower surrounded by ferns, the plunge pool at dusk, the absolute silence except for frogs — it's the most romantic place I've ever been.",
     'textZh': "在此度蜜月。被蕨类植物环绕的户外雨淋浴、黄昏时分的小泳池、除青蛙鸣叫外的绝对静谧——这是我去过最浪漫的地方。",
     'cleanliness': '10', 'accuracy': '10', 'location': '10', 'value': '9'},
    {'villaId': 'villa-7', 'guestName': 'Sarah M.', 'rating': '9.8', 'date': '2026-01-20',
     'textEn': "I will dream of this villa for years. The way the morning light hits the rice terraces through the bedroom windows is unlike anything I've experienced. Made is the perfect host — never intrusive, always there.",
     'textZh': "我会多年梦见这栋别墅。清晨的光线透过卧室窗户照射稻田的方式，是我从未体验过的景象。Made是完美的房东——从不打扰，却始终在场。",
     'cleanliness': '10', 'accuracy': '10', 'location': '10', 'value': '9'},
    # villa-8 Batu Uluwatu
    {'villaId': 'villa-8', 'guestName': '李明', 'rating': '9.4', 'date': '2026-04-12',
     'textEn': "Surfed Bingin every day from this base. The walk down to the beach is steep but worth every step. Ketut arranged everything from airport pickup to a drone photographer for our surf photos.",
     'textZh': "以此为基地每天去滨金冲浪。下海滩的路很陡但每一步都值得。Ketut安排了从机场接送到冲浪无人机摄影的一切。",
     'cleanliness': '9', 'accuracy': '9', 'location': '10', 'value': '9'},
    {'villaId': 'villa-8', 'guestName': '林敏', 'rating': '9.2', 'date': '2026-02-28',
     'textEn': "A romantic surf trip. The villa is built into the cliff and the atmosphere is completely unique. Watching the sunset over the Indian Ocean from the pool with a Bintang in hand — that's what Bali dreams are made of.",
     'textZh': "一次浪漫的冲浪之旅。别墅建于悬崖之上，氛围独一无二。手持宾坦啤酒在泳池边欣赏印度洋日落——这就是巴厘岛梦想的模样。",
     'cleanliness': '9', 'accuracy': '9', 'location': '10', 'value': '8'},
    # villa-9 Pantai Seminyak
    {'villaId': 'villa-9', 'guestName': '陈静', 'rating': '9.0', 'date': '2026-03-30',
     'textEn': "Good value for central Seminyak. Location is everything here — walked to Potato Head and La Favela in the evenings. The pool is smaller than it looks in photos but still very pleasant.",
     'textZh': "对水明漾中心地带来说性价比不错。地理位置就是一切——傍晚步行去薯头海滩俱乐部和La Favela。泳池比照片中看起来小一些，但仍然非常惬意。",
     'cleanliness': '9', 'accuracy': '8', 'location': '10', 'value': '8'},
    {'villaId': 'villa-9', 'guestName': '刘洋', 'rating': '9.2', 'date': '2026-04-03',
     'textEn': "Pre-wedding trip for six of us. Seminyak is perfect for this — amazing restaurants, beach clubs, and the villa to come back to when you need a break from the fun. Nyoman was incredibly responsive.",
     'textZh': "六人婚前旅行。水明漾非常适合这种场合——精彩的餐厅、海滩俱乐部，玩累了可以回到别墅休息。Nyoman的回复速度令人印象深刻。",
     'cleanliness': '9', 'accuracy': '9', 'location': '10', 'value': '8'},
    # villa-10 Pererenan Canggu
    {'villaId': 'villa-10', 'guestName': '王芳', 'rating': '9.2', 'date': '2026-04-08',
     'textEn': "The rooftop BBQ was our nightly ritual — the Canggu sunset from up there is incredible. Putu's team was always discreet and helpful. Great value compared to the villas closer to the main strip.",
     'textZh': "屋顶烧烤成了我们每晚的仪式——从那里俯瞰水流通的日落美景令人叹为观止。Putu的团队始终低调而专业。与靠近主街道的别墅相比，性价比极高。",
     'cleanliness': '9', 'accuracy': '9', 'location': '9', 'value': '10'},
    # villa-11 Sindhu Sanur
    {'villaId': 'villa-11', 'guestName': '张伟', 'rating': '9.2', 'date': '2026-03-25',
     'textEn': "Sanur is underrated. This villa is a hidden gem in a neighbourhood that feels lived-in and authentic. The shallow wading pool section was a lifesaver with our three-year-old.",
     'textZh': "沙努尔被低估了。这栋别墅是一个隐藏的宝藏，所在街区充满生活气息和原真性。浅水区对我们三岁的孩子来说是救星。",
     'cleanliness': '9', 'accuracy': '9', 'location': '9', 'value': '9'},
    {'villaId': 'villa-11', 'guestName': '赵晓丽', 'rating': '9.0', 'date': '2026-02-05',
     'textEn': "Sanur surprised us — it's much more local and charming than the south. The morning beach walk with the fishing boats at sunrise was a daily treat. Putu sorted a fantastic day trip to Nusa Penida for us.",
     'textZh': "沙努尔让我们大吃一惊——比南部更具本土气息和魅力。日出时分与渔船为伴的晨间海滩漫步成了每日的享受。Putu为我们安排了一次精彩的努沙佩尼达一日游。",
     'cleanliness': '9', 'accuracy': '9', 'location': '9', 'value': '9'},
    # villa-12 Tanjung Nusa Dua
    {'villaId': 'villa-12', 'guestName': '黄海', 'rating': '9.6', 'date': '2026-04-28',
     'textEn': "Celebrated my 40th here with family. The private beach is real — no sunbeds to fight for, just white sand and your people. Made personally ensured every detail of our welcome dinner was perfect.",
     'textZh': "在此与家人庆祝四十岁生日。私人海滩名副其实——不需要抢占躺椅，只有白沙和您挚爱的人。Made亲自确保我们欢迎晚宴的每个细节都臻于完美。",
     'cleanliness': '10', 'accuracy': '10', 'location': '9', 'value': '9'},
]

BOOKINGS_DATA = [
    {'reference': 'BV-2026-04781', 'villaId': 'villa-7', 'status': 'confirmed',
     'checkIn': '2026-06-12', 'checkOut': '2026-06-19', 'nights': 7,
     'adults': 2, 'children': 0, 'infants': 0,
     'totalCny': '10395', 'totalIdr': '22400000', 'paymentMethod': 'wechat_pay', 'paidAt': '2026-05-10T08:24:00Z'},
    {'reference': 'BV-2026-03922', 'villaId': 'villa-4', 'status': 'confirmed',
     'checkIn': '2026-07-03', 'checkOut': '2026-07-08', 'nights': 5,
     'adults': 4, 'children': 0, 'infants': 0,
     'totalCny': '12760', 'totalIdr': '27500000', 'paymentMethod': 'alipay', 'paidAt': '2026-05-15T14:33:00Z'},
    {'reference': 'BV-2025-18740', 'villaId': 'villa-1', 'status': 'completed',
     'checkIn': '2025-12-26', 'checkOut': '2026-01-02', 'nights': 7,
     'adults': 2, 'children': 1, 'infants': 0,
     'totalCny': '14616', 'totalIdr': '31500000', 'paymentMethod': 'wechat_pay', 'paidAt': '2025-12-10T09:11:00Z'},
    {'reference': 'BV-2025-14203', 'villaId': 'villa-9', 'status': 'completed',
     'checkIn': '2025-10-18', 'checkOut': '2025-10-23', 'nights': 5,
     'adults': 6, 'children': 0, 'infants': 0,
     'totalCny': '22035', 'totalIdr': '47500000', 'paymentMethod': 'unionpay', 'paidAt': '2025-09-30T16:42:00Z'},
    {'reference': 'BV-2026-02841', 'villaId': 'villa-2', 'status': 'pending_approval',
     'checkIn': '2026-08-15', 'checkOut': '2026-08-22', 'nights': 7,
     'adults': 4, 'children': 2, 'infants': 0,
     'totalCny': '27594', 'totalIdr': '59500000', 'paymentMethod': None, 'paidAt': None},
    {'reference': 'BV-2025-09182', 'villaId': 'villa-5', 'status': 'cancelled',
     'checkIn': '2025-08-05', 'checkOut': '2025-08-12', 'nights': 7,
     'adults': 2, 'children': 2, 'infants': 1,
     'totalCny': '23387', 'totalIdr': '50400000', 'paymentMethod': 'wechat_pay', 'paidAt': '2025-07-01T07:55:00Z',
     'cancelledAt': '2025-07-20T15:22:00Z', 'cancellationReason': 'Travel plans changed'},
    {'reference': 'BV-2026-05102', 'villaId': 'villa-11', 'status': 'confirmed',
     'checkIn': '2026-09-01', 'checkOut': '2026-09-06', 'nights': 5,
     'adults': 2, 'children': 2, 'infants': 0,
     'totalCny': '13455', 'totalIdr': '29000000', 'paymentMethod': 'alipay', 'paidAt': '2026-05-19T10:15:00Z'},
    {'reference': 'BV-2025-22019', 'villaId': 'villa-3', 'status': 'completed',
     'checkIn': '2025-12-01', 'checkOut': '2025-12-05', 'nights': 4,
     'adults': 8, 'children': 0, 'infants': 0,
     'totalCny': '22272', 'totalIdr': '48000000', 'paymentMethod': 'card', 'paidAt': '2025-11-15T13:20:00Z'},
]

# Conversations with nested messages — all from the demo guest (李明)
CONVERSATIONS_DATA = [
    {
        'id': 'conv-1', 'villaId': 'villa-7', 'hostId': 'host-2', 'lastMessageAt': '2026-05-18T14:32:00Z', 'unreadGuest': 2,
        'messages': [
            {'id': 'msg-1-1', 'sender': 'guest', 'textZh': '你好，请问6月12日到6月19日别墅还有空房吗？我们两人，想要一个安静的假期。', 'textEn': 'Hello, is the villa available from June 12 to June 19? There are two of us, looking for a quiet retreat.', 'sentAt': '2026-05-17T09:15:00Z', 'translated': True},
            {'id': 'msg-1-2', 'sender': 'host', 'textEn': "Hi! Great news — those dates are available. Villa Sawah is perfect for couples seeking peace. The rice terraces are at their most beautiful in June. Shall I hold the dates for you?", 'textZh': '您好！好消息——那些日期有空房。稻田别墅非常适合寻求宁静的情侣。六月份的稻田景色最为美丽。我帮您预留那几天吗？', 'sentAt': '2026-05-17T09:48:00Z', 'translated': True},
            {'id': 'msg-1-3', 'sender': 'guest', 'textZh': '太好了！请问可以安排私人厨师吗？我们希望有一顿特别的晚餐。', 'textEn': 'Great! Can a private chef be arranged? We would like one special dinner.', 'sentAt': '2026-05-17T10:02:00Z', 'translated': True},
            {'id': 'msg-1-4', 'sender': 'host', 'textEn': "Absolutely! Our chef Kadek specialises in both Balinese and Chinese cuisine. A 4-course dinner for two runs around Rp 800,000 (≈ ¥370). I can arrange flowers and candles by the pool at no extra charge — just say the word.", 'textZh': '当然可以！我们的厨师Kadek擅长巴厘岛和中式菜肴。两人四道菜晚餐约Rp 800,000（约¥370）。我可以免费在泳池旁布置鲜花和蜡烛——告诉我一声就好。', 'sentAt': '2026-05-17T10:31:00Z', 'translated': True},
            {'id': 'msg-1-5', 'sender': 'guest', 'textZh': '非常好！我们今天就预订。谢谢您的热情款待。', 'textEn': 'Perfect! We will book today. Thank you for your warm hospitality.', 'sentAt': '2026-05-17T10:45:00Z', 'translated': True},
            {'id': 'msg-1-6', 'sender': 'host', 'textEn': "Wonderful! I've noted the chef dinner request. On arrival day, I'll be there personally to welcome you and show you around. Welcome to Villa Sawah — we can't wait to host you.", 'textZh': '太棒了！我已记下厨师晚餐的要求。抵达当天，我会亲自迎接您并带您参观。欢迎来到稻田别墅——我们迫不及待地等待接待您。', 'sentAt': '2026-05-17T11:05:00Z', 'translated': True},
            {'id': 'msg-1-7', 'sender': 'guest', 'textZh': '请问别墅距离乌布市场有多远？', 'textEn': 'How far is the villa from the Ubud market?', 'sentAt': '2026-05-18T14:20:00Z', 'translated': True},
            {'id': 'msg-1-8', 'sender': 'host', 'textEn': "About 15 minutes by scooter (I can arrange one for you), or 30 minutes by car. The morning market at Ubud is best visited early — around 6am before the tour groups arrive.", 'textZh': '骑摩托车约15分钟（我可以为您安排），或乘车约30分钟。乌布早市最好早去——大约早上6点，在旅游团到达之前。', 'sentAt': '2026-05-18T14:32:00Z', 'translated': False},
        ],
    },
    {
        'id': 'conv-2', 'villaId': 'villa-4', 'hostId': 'host-4', 'lastMessageAt': '2026-05-15T16:44:00Z', 'unreadGuest': 0,
        'messages': [
            {'id': 'msg-2-1', 'sender': 'guest', 'textZh': '你好，请问别墅附近有冲浪板租赁吗？我们是初学者。', 'textEn': 'Hi, is there surfboard rental near the villa? We are beginners.', 'sentAt': '2026-05-14T11:20:00Z', 'translated': True},
            {'id': 'msg-2-2', 'sender': 'host', 'textEn': "Hello! Yes — Batu Bolong Beach is a 2-minute walk and there are three board rental spots right there. For beginners I recommend Dewa Surf Shop (ask for Dewa, tell him I sent you — he'll give you a good price). Lessons are also available.", 'textZh': '您好！是的——芭杜博朗海滩步行2分钟，那里有三家冲浪板租赁店。初学者我推荐Dewa冲浪店（向Dewa说是我介绍的——他会给您好价格）。也提供冲浪课程。', 'sentAt': '2026-05-14T11:55:00Z', 'translated': True},
            {'id': 'msg-2-3', 'sender': 'guest', 'textZh': '太好了！请问提前退房有什么手续吗？', 'textEn': 'Great! Is there a process for early check-out?', 'sentAt': '2026-05-14T12:05:00Z', 'translated': True},
            {'id': 'msg-2-4', 'sender': 'host', 'textEn': "Just let me know the evening before and the team will prepare everything. There's no early checkout fee. Can I ask what time your flight is? I can arrange a driver to the airport.", 'textZh': '提前一晚通知我，团队会做好一切准备。没有提前退房费用。请问您的航班几点？我可以安排司机送您去机场。', 'sentAt': '2026-05-14T12:20:00Z', 'translated': True},
            {'id': 'msg-2-5', 'sender': 'guest', 'textZh': '我们的航班是上午10点。需要大约几点出发？', 'textEn': 'Our flight is at 10am. Around what time should we leave?', 'sentAt': '2026-05-15T09:30:00Z', 'translated': True},
            {'id': 'msg-2-6', 'sender': 'host', 'textEn': "For a 10am flight I'd suggest leaving by 7:30am. Ngurah Rai can be unpredictable. I'll arrange your driver for 7:15am — confirmed?", 'textZh': '10点的航班建议7:30出发。伍拉·赖机场交通有时难以预测。我将为您安排7:15的司机——确认吗？', 'sentAt': '2026-05-15T16:44:00Z', 'translated': True},
        ],
    },
    {
        'id': 'conv-3', 'villaId': 'villa-2', 'hostId': 'host-2', 'lastMessageAt': '2026-05-01T19:22:00Z', 'unreadGuest': 0,
        'messages': [
            {'id': 'msg-3-1', 'sender': 'guest', 'textZh': '你好！我看到你们有时候会提供直升机接送服务，这个是真的吗？', 'textEn': 'Hi! I saw that sometimes helicopter transfers are available. Is that true?', 'sentAt': '2026-04-29T14:10:00Z', 'translated': True},
            {'id': 'msg-3-2', 'sender': 'host', 'textEn': "Yes! We can arrange helicopter transfers from the airport or from Ubud. It's spectacular flying in over the cliffs. The cost is around USD 450 one-way for the helicopter (seats 4). Want me to check availability for your dates?", 'textZh': '是的！我们可以安排从机场或乌布的直升机接送。飞越悬崖时的景色壮观无比。单程费用约450美元（4人座）。需要我查询您日期的可用性吗？', 'sentAt': '2026-04-29T14:45:00Z', 'translated': True},
            {'id': 'msg-3-3', 'sender': 'guest', 'textZh': '太棒了！不过这次我们选择地面交通就好。但是下次一定要试试！请问从机场到别墅大概需要多长时间？', 'textEn': "That's amazing! We'll stick to ground transport this time, but will definitely try it next visit! How long does it take from the airport?", 'sentAt': '2026-04-30T09:22:00Z', 'translated': True},
            {'id': 'msg-3-4', 'sender': 'host', 'textEn': "By car it's about 45–60 minutes depending on traffic. I'll send our dedicated driver — he'll have a BaliVilla sign and cold water waiting. The drive through the rice fields of Jimbaran is beautiful.", 'textZh': '开车大约45-60分钟，视交通情况而定。我会派我们的专属司机——他会举着BaliVilla的牌子，备有冰水等候。经过金巴兰稻田的路途非常美丽。', 'sentAt': '2026-04-30T10:05:00Z', 'translated': True},
            {'id': 'msg-3-5', 'sender': 'guest', 'textZh': '好的，谢谢！我们期待这次旅行。', 'textEn': 'Perfect, thank you! We are really looking forward to the trip.', 'sentAt': '2026-05-01T19:22:00Z', 'translated': True},
        ],
    },
    {
        'id': 'conv-4', 'villaId': 'villa-9', 'hostId': 'host-4', 'lastMessageAt': '2025-10-23T08:15:00Z', 'unreadGuest': 0,
        'messages': [
            {'id': 'msg-4-1', 'sender': 'host', 'textEn': "Hi! Just checking in — your group arrives tomorrow. Everything is ready at Villa Pantai. The pool has been freshly cleaned, the fridge is stocked, and the AC is running to pre-cool the villa. See you tomorrow!", 'textZh': '您好！只是确认一下——您的团队明天到达。海滩别墅一切准备就绪。泳池已清洁完毕，冰箱已备货，空调正在运行以预先冷却别墅。明天见！', 'sentAt': '2025-10-17T16:00:00Z', 'translated': True},
            {'id': 'msg-4-2', 'sender': 'guest', 'textZh': '非常感谢！请问我们可以晚上10点到达吗？', 'textEn': 'Thank you! Can we arrive at 10pm?', 'sentAt': '2025-10-17T18:40:00Z', 'translated': True},
            {'id': 'msg-4-3', 'sender': 'host', 'textEn': "Of course! Late arrival is no problem at all. The villa team will be there to greet you. I'll leave the welcome drinks on ice.", 'textZh': '当然！晚到完全没问题。别墅团队会在那里迎接您。我会把迎宾饮料放在冰上。', 'sentAt': '2025-10-17T19:02:00Z', 'translated': True},
            {'id': 'msg-4-4', 'sender': 'guest', 'textZh': '太好了！我们非常期待这次旅行。这是我们公司团建活动。', 'textEn': "Great! We're very excited. This is our company team-building trip.", 'sentAt': '2025-10-17T19:15:00Z', 'translated': True},
            {'id': 'msg-4-5', 'sender': 'host', 'textEn': "How exciting! I've arranged some extra poolside seating for your group. If you need anything during the stay — restaurant bookings, transport, activities — just message me any time.", 'textZh': '太令人兴奋了！我已为您的团队安排了额外的泳池边座位。如果住宿期间需要任何帮助——餐厅预订、交通、活动——随时给我发消息。', 'sentAt': '2025-10-17T19:30:00Z', 'translated': True},
            {'id': 'msg-4-6', 'sender': 'guest', 'textZh': '感谢您的周到服务！再见！', 'textEn': 'Thank you for the thoughtful service! See you soon!', 'sentAt': '2025-10-17T19:45:00Z', 'translated': True},
            {'id': 'msg-4-7', 'sender': 'guest', 'textZh': '我们刚刚安全到达，别墅非常漂亮！谢谢您！', 'textEn': "We've just arrived safely, the villa is beautiful! Thank you!", 'sentAt': '2025-10-18T22:40:00Z', 'translated': True},
            {'id': 'msg-4-8', 'sender': 'host', 'textEn': "So glad to hear it! Enjoy every moment. Don't forget breakfast at the pool starts at 7:30am. Sleep well!", 'textZh': '很高兴听到这个消息！尽情享受每一刻。别忘了泳池边的早餐从早上7:30开始供应。好好休息！', 'sentAt': '2025-10-23T08:15:00Z', 'translated': True},
        ],
    },
]

# ─── command ─────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Seeds the database with mock demo data (idempotent — clears existing data first)'

    def handle(self, *args, **options):
        self.stdout.write('Clearing existing data...')
        self._clear()

        self.stdout.write('Seeding hosts...')
        hosts = self._seed_hosts()

        self.stdout.write('Seeding guest users...')
        guest_map = self._seed_guests()

        self.stdout.write('Seeding villas...')
        villas = self._seed_villas(hosts)

        self.stdout.write('Seeding bookings...')
        bookings = self._seed_bookings(guest_map['李明'], villas)

        self.stdout.write('Seeding reviews...')
        self._seed_reviews(villas, guest_map)

        self.stdout.write('Seeding conversations...')
        self._seed_conversations(villas, hosts, guest_map['李明'])

        self.stdout.write('Seeding availability...')
        self._seed_availability(villas)

        self.stdout.write('Seeding wishlists...')
        self._seed_wishlists(villas, guest_map)

        self.stdout.write(self.style.SUCCESS(
            f'Done — {len(villas)} villas, {len(hosts)} hosts, '
            f'{Review.objects.count()} reviews, {Booking.objects.count()} bookings, '
            f'{Conversation.objects.count()} conversations, '
            f'{Availability.objects.count()} availability rows, '
            f'{Wishlist.objects.count()} wishlist entries'
        ))

    def _clear(self):
        Review.objects.all().delete()
        Message.objects.all().delete()
        Conversation.objects.all().delete()
        Payment.objects.all().delete()
        Booking.objects.all().delete()
        Availability.objects.all().delete()
        Villa.objects.all().delete()        # cascades photos, amenities, wishlists
        HostProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _seed_hosts(self) -> dict:
        host_map = {}
        for d in HOSTS_DATA:
            user, _ = User.objects.get_or_create(
                email=d['email'],
                defaults={
                    'first_name': d['first_name'],
                    'last_name': d['last_name'],
                    'avatar_url': d['avatar'],
                    'locale': 'en',
                    'preferred_language': 'id',
                    'roles': ['host'],
                    'is_active': True,
                    'email_verified': True,
                },
            )
            user.set_password('demo1234')
            user.save()

            profile, _ = HostProfile.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': d['display_name'],
                    'bio': d['bio'],
                    'languages': d['languages'],
                    'response_rate': Decimal(d['response_rate']),
                    'hosting_since': d['hosting_since'],
                    'total_revenue_idr': Decimal(d['total_revenue_idr']),
                    'avg_rating': Decimal(d['avg_rating']),
                    'total_bookings': d['total_bookings'],
                    'is_verified': True,
                    'kyc_status': HostProfile.KYC_APPROVED,
                },
            )
            host_map[d['id']] = profile
        return host_map

    def _seed_guests(self) -> dict:
        guest_map = {}
        for name, slug, bg in GUEST_REVIEWERS:
            email = f'{slug}@demo.balivilla.dev'
            is_zh = any('一' <= c <= '鿿' for c in name)
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': name.split()[0],
                    'last_name': name.split()[-1] if ' ' in name else '',
                    'avatar_url': av(name, bg),
                    'locale': 'zh' if is_zh else 'en',
                    'preferred_language': 'zh' if is_zh else 'en',
                    'roles': ['guest'],
                    'is_active': True,
                    'email_verified': True,
                },
            )
            user.set_password('demo1234')
            user.save()
            guest_map[name] = user
        return guest_map

    def _seed_villas(self, host_map: dict) -> dict:
        villa_map = {}
        for d in VILLAS_DATA:
            host = host_map[d['hostId']]
            villa = Villa.objects.create(
                slug=d['slug'],
                host=host,
                title_en=d['titleEn'],
                title_zh=d['titleZh'],
                description_en=d['descriptionEn'],
                description_zh=d['descriptionZh'],
                location=d['location'],
                region=d['region'],
                bedrooms=d['bedrooms'],
                beds=d.get('beds', d['bedrooms']),
                highlights=d.get('highlights', []),
                bathrooms=d['bathrooms'],
                max_guests=d['maxGuests'],
                pool='pool' in d['amenities'],
                base_price_idr=Decimal(d['basePriceIdr']),
                base_price_cny=Decimal(d['basePriceCny']),
                avg_rating=Decimal(d['rating']),
                review_count=d['reviewCount'],
                instant_book=d['isInstantBook'],
                status=Villa.STATUS_PUBLISHED,
                is_verified=True,
                tags=d['badges'],
                cover_photo_url=PHOTOS.get(d['photos'][0], ''),
            )
            for i, key in enumerate(d['photos']):
                VillaPhoto.objects.create(villa=villa, url=PHOTOS.get(key, ''), order=i)
            for key in d['amenities']:
                info = AMENITY_INFO.get(key, (key, key, 'essentials', False))
                VillaAmenity.objects.create(
                    villa=villa, key=key,
                    label_en=info[0], label_zh=info[1],
                    category=info[2], is_highlight=info[3],
                )
            villa_map[d['id']] = villa
        return villa_map

    def _seed_bookings(self, guest: User, villa_map: dict) -> dict:
        from django.utils.dateparse import parse_datetime, parse_date
        booking_map = {}
        for d in BOOKINGS_DATA:
            cancelled_at = parse_datetime(d['cancelledAt']) if d.get('cancelledAt') else None
            booking = Booking.objects.create(
                reference=d['reference'],
                guest=guest,
                villa=villa_map[d['villaId']],
                check_in=parse_date(d['checkIn']),
                check_out=parse_date(d['checkOut']),
                nights=d['nights'],
                adults=d['adults'],
                children=d['children'],
                infants=d['infants'],
                nightly_rate_idr=Decimal(d['totalIdr']),
                total_idr=Decimal(d['totalIdr']),
                base_price_cny=Decimal(d['totalCny']),
                total_cny=Decimal(d['totalCny']),
                payout_idr=Decimal(d['totalIdr']) * Decimal('0.88'),
                status=d['status'],
                cancelled_at=cancelled_at,
                cancellation_reason=d.get('cancellationReason', ''),
            )
            booking_map[d['reference']] = booking
            # Create a Payment record for bookings that have been paid
            if d.get('paymentMethod'):
                pay_status = (
                    Payment.STATUS_REFUNDED if d['status'] == 'cancelled'
                    else Payment.STATUS_SUCCESS
                )
                Payment.objects.create(
                    booking=booking,
                    awx_payment_intent_id=f'seed-{d["reference"]}',
                    method=d['paymentMethod'],
                    status=pay_status,
                    amount_cny=Decimal(d['totalCny']),
                    amount_idr=Decimal(d['totalIdr']),
                )
        return booking_map

    def _seed_reviews(self, villa_map: dict, guest_map: dict):
        from django.utils.dateparse import parse_date
        import datetime
        for d in REVIEWS_DATA:
            guest = guest_map.get(d['guestName'])
            if not guest:
                continue
            villa = villa_map.get(d['villaId'])
            if not villa:
                continue
            is_zh_guest = any('一' <= c <= '鿿' for c in d['guestName'])
            if is_zh_guest:
                orig, orig_lang, trans, trans_lang = d['textZh'], 'zh', d['textEn'], 'en'
            else:
                orig, orig_lang, trans, trans_lang = d['textEn'], 'en', d['textZh'], 'zh'
            review = Review.objects.create(
                guest=guest,
                villa=villa,
                booking=None,
                rating=Decimal(d['rating']),
                rating_cleanliness=Decimal(d['cleanliness']),
                rating_accuracy=Decimal(d['accuracy']),
                rating_checkin=Decimal(d.get('checkin', '9')),
                rating_communication=Decimal(d.get('communication', '9')),
                rating_location=Decimal(d['location']),
                rating_value=Decimal(d['value']),
                text_original=orig,
                text_original_lang=orig_lang,
                text_translated=trans,
                text_translated_lang=trans_lang,
            )
            if d.get('date'):
                pd = parse_date(d['date'])
                created = datetime.datetime(pd.year, pd.month, pd.day, 12, 0, 0, tzinfo=datetime.timezone.utc)
                Review.objects.filter(pk=review.pk).update(published_at=created)

    def _seed_conversations(self, villa_map: dict, host_map: dict, guest: User):
        from django.utils.dateparse import parse_datetime
        for c in CONVERSATIONS_DATA:
            villa = villa_map.get(c['villaId'])
            host_profile = host_map[c['hostId']]
            conv = Conversation.objects.create(
                guest=guest,
                host=host_profile,
                villa=villa,
                last_message_at=parse_datetime(c['lastMessageAt']),
                guest_unread_count=c['unreadGuest'],
            )
            for m in c['messages']:
                if m['sender'] == 'guest':
                    sender = guest
                    orig, orig_lang = m['textZh'], 'zh'
                    trans = m['textEn'] if m['translated'] else ''
                    trans_lang = 'en' if m['translated'] else ''
                else:
                    sender = host_profile.user
                    orig, orig_lang = m['textEn'], 'en'
                    trans = m['textZh'] if m['translated'] else ''
                    trans_lang = 'zh' if m['translated'] else ''
                # Build translations dict from seed's pre-written bilingual text
                translations = {orig_lang: orig}
                if trans:
                    translations[trans_lang] = trans
                Message.objects.create(
                    conversation=conv,
                    sender=sender,
                    body_original=orig,
                    body_original_lang=orig_lang,
                    translations=translations,
                    body_translated=trans,
                    body_translated_lang=trans_lang,
                )
            # Set last message preview from most recent message
            last = c['messages'][-1]
            preview = last['textZh'] if last['sender'] == 'guest' else last['textEn']
            conv.last_message_preview = preview[:299]
            conv.save()

    def _seed_availability(self, villa_map: dict):
        """90 days of availability for every villa with realistic blocked dates and weekend pricing."""
        rng = random.Random(42)  # fixed seed → reproducible results
        today = date.today()
        bulk = []
        for villa in villa_map.values():
            weekend_premium = Decimal(str(villa.weekend_premium_pct)) / Decimal('100')
            for offset in range(90):
                d = today + timedelta(days=offset)
                # ~18% of dates blocked (simulates existing bookings / owner blocks)
                if rng.random() < 0.18:
                    bulk.append(Availability(villa=villa, date=d, status=Availability.STATUS_BLOCKED))
                    continue
                # Weekend premium price override
                is_weekend = d.weekday() in (4, 5)  # Fri, Sat
                price_override = None
                if is_weekend and weekend_premium:
                    price_override = (villa.base_price_idr * (1 + weekend_premium)).quantize(Decimal('1000'))
                # 3% of weekdays get a "holiday" price bump
                elif d.weekday() not in (4, 5) and rng.random() < 0.03:
                    price_override = (villa.base_price_idr * Decimal('1.30')).quantize(Decimal('1000'))
                bulk.append(Availability(
                    villa=villa,
                    date=d,
                    status=Availability.STATUS_AVAILABLE,
                    price_override_idr=price_override,
                ))
        Availability.objects.bulk_create(bulk, ignore_conflicts=True)

    def _seed_wishlists(self, villa_map: dict, guest_map: dict):
        """Give each guest 2-3 random villas on their wishlist."""
        rng = random.Random(99)
        villa_list = list(villa_map.values())
        bulk = []
        for guest in guest_map.values():
            picks = rng.sample(villa_list, min(3, len(villa_list)))
            for villa in picks:
                bulk.append(Wishlist(user=guest, villa=villa))
        Wishlist.objects.bulk_create(bulk, ignore_conflicts=True)
