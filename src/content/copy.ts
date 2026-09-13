import type { Locale, SiteCopy } from './types';

export const copy = {
  uk: {
    navigation: {
      label: 'Головна навігація',
      home: 'На головну',
      programmes: 'Програми',
      method: 'Методика',
      coaching: 'Супровід',
      equipment: 'Спорядження',
      openMenu: 'Відкрити меню',
      closeMenu: 'Закрити меню',
      language: 'Мова інтерфейсу',
      skip: 'Перейти до основного вмісту',
    },
    hero: {
      line1: 'Стійка на руках.',
      line2: 'У твоєму ритмі.',
      description: 'Сила, рухливість і баланс — крок за кроком.',
      action: 'Обрати програму',
      imageAlt: 'Стійка на руках на темному тлі.',
    },
    programmes: {
      eyebrow: 'Напрями практики',
      title: 'Знайди свій напрям.',
      description: 'Розвивай силу, рухливість і звичку до регулярного руху.',
      imageAlt: 'Людина виконує сидячу вправу на рухливість у темній студії.',
    },
    method: {
      eyebrow: 'Методика',
      title: 'Кожен крок має сенс.',
      description: 'Від стартового рівня до наступного кроку — з увагою до твоєї практики.',
      steps: [
        {
          title: 'Стартовий рівень',
          body: 'Врахувати твій досвід, цілі й запитання перед вибором напряму.',
        },
        {
          title: 'Послідовна практика',
          body: 'Обрати структуру занять, до якої можна повертатися.',
        },
        {
          title: 'Увага до прогресу',
          body: 'Помічати зміни й переглядати наступні кроки у своїй практиці.',
        },
      ],
    },
    coaching: {
      eyebrow: 'Формати підтримки',
      title: 'Твоя практика. З підтримкою.',
      description: 'Від самостійної програми до розмови й зворотного зв’язку тренера.',
      compareLabel: 'Порівняти пакети',
      bundleLabel: 'Програма та особиста розмова',
    },
    equipment: {
      eyebrow: 'Спорядження',
      title: 'Простір для практики.',
      description: 'Концепти спорядження для стійки, рухливості й вправ на підлозі.',
      imageAlt: 'Спорядження для практики: паралетси, килимок і блоки.',
    },
    future: {
      eyebrow: 'Майбутній напрям',
      title: 'Більше контексту для твоєї практики.',
      body: 'Плануємо платформу з історією тренувань, AI-поясненнями й аналізом відео. Ці можливості ще не доступні й не входять до пакетів цього концепту. Робота з відео потребуватиме окремої згоди.',
      items: ['Журнал тренувань', 'AI-пояснення', 'Аналіз відео'],
    },
    faq: {
      eyebrow: 'Запитання',
      title: 'Перед початком.',
      items: [
        {
          id: 'start',
          question: 'З чого почати?',
          answer:
            'Переглянь напрями й визнач, над чим хочеш працювати. Формат консультації 1:1 передбачений для обговорення цілей і запитань перед вибором програми.',
        },
        {
          id: 'mobility',
          question: 'Яка роль рухливості?',
          answer:
            'Цей напрям зосереджений на амплітуді й контролі рухів. Конкретний зміст практики залежатиме від обраної програми.',
        },
        {
          id: 'coaching',
          question: 'Чим програма відрізняється від супроводу?',
          answer:
            'Програма задає структуру самостійної практики. Супровід додає зворотний зв’язок тренера. Його формат і частота ще уточнюються.',
        },
        {
          id: 'platform',
          question: 'Чи вже доступні журнал і AI-функції?',
          answer:
            'Поки ні. Журнал тренувань, AI-пояснення й аналіз відео — майбутні напрями платформи. Вони не входять до доступних функцій цього концепту.',
        },
      ],
    },
    footer: {
      title: 'Твій наступний крок.',
      action: 'Переглянути програми',
      note: 'Концепт студії. Програми, комплектація й доступність уточнюються.',
      top: 'На початок сторінки',
    },
    common: {
      details: 'Детальніше',
      close: 'Закрити',
      concept: 'Концепт пропозиції',
      included: 'У фокусі пропозиції',
      offerNote: 'Це запропонований формат. Склад, умови доступу та підтримки ще уточнюються.',
      equipmentNote: 'Концепт асортименту. Моделі, характеристики й доступність ще не визначені.',
      photoNote:
        'Зображення згенеровані для концепту. Вони не представляють тренера студії чи навчальні демонстрації.',
    },
    offers: {
      handstand: {
        title: 'Стійка на руках',
        summary: 'Опора, положення тіла й баланс.',
        description:
          'Практика стійки з увагою до опори, положення тіла та кожного наступного кроку.',
        includes: ['Опора на руки', 'Положення тіла', 'Баланс'],
      },
      mobility: {
        title: 'Сила та рухливість',
        summary: 'Сила й контроль у русі.',
        description: 'Робота над силою й контролем рухів як частина твоєї регулярної практики.',
        includes: ['Сила', 'Рухливість', 'Контроль рухів'],
      },
      flexibility: {
        title: 'Гнучкість',
        summary: 'Досліджуй амплітуду без поспіху.',
        description:
          'Послідовна робота з амплітудою рухів, без поспіху й гонитви за складними позами.',
        includes: ['Амплітуда рухів', 'Увага до відчуттів', 'Послідовна практика'],
      },
      programme: {
        title: 'Programme',
        summary: 'Один напрям. Власний ритм.',
        description: 'Одна обрана програма для послідовної самостійної практики.',
        includes: ['Обрана програма', 'Структура практики', 'Самостійний формат'],
      },
      studio: {
        title: 'Studio',
        summary: 'Кілька напрямів для твоєї практики.',
        description: 'Набір програм, щоб поєднувати різні напрями у своїй практиці.',
        includes: ['Набір програм', 'Різні напрями', 'Самостійна практика'],
      },
      coach: {
        title: 'Coach+',
        summary: 'Практика зі зворотним зв’язком.',
        description:
          'Програми зі зворотним зв’язком тренера для обговорення твоєї практики й наступних кроків.',
        includes: ['Програми', 'Зворотний зв’язок тренера', 'Обговорення наступних кроків'],
      },
      consultation: {
        title: 'Консультація 1:1',
        summary: 'Простір для твоїх запитань.',
        description:
          'Розмова про твої цілі, досвід і запитання, щоб визначити напрям подальшої практики.',
        includes: ['Цілі й досвід', 'Запитання до практики', 'Напрям подальшої роботи'],
      },
      bundle: {
        title: 'Програма + консультація',
        summary: 'Структура й особиста розмова.',
        description:
          'Самостійна практика й окрема розмова з тренером, щоб розібрати запитання до програми.',
        includes: ['Обрана програма', 'Консультація 1:1', 'Обговорення запитань'],
      },
      parallettes: {
        title: 'Паралетси',
        summary: 'Опори для практики.',
        description:
          'Концепт опор для практики стійки та силових елементів. Конкретну модель ще не визначено.',
        includes: ['Практика опори', 'Силові елементи'],
      },
      mat: {
        title: 'Килимок для практики',
        summary: 'Місце для руху.',
        description:
          'Концепт килимка для вправ на підлозі. Матеріали, розміри й комплектація ще уточнюються.',
        includes: ['Практика на підлозі', 'Рухливість і гнучкість'],
      },
      blocks: {
        title: 'Блоки для практики',
        summary: 'Додаткова опора.',
        description:
          'Концепт блоків для окремих вправ на рухливість і гнучкість. Модель і характеристики ще уточнюються.',
        includes: ['Додаткова опора', 'Рухливість і гнучкість'],
      },
    },
  },
  en: {
    navigation: {
      label: 'Main navigation',
      home: 'Home',
      programmes: 'Programmes',
      method: 'Method',
      coaching: 'Coaching',
      equipment: 'Equipment',
      openMenu: 'Open menu',
      closeMenu: 'Close menu',
      language: 'Interface language',
      skip: 'Skip to main content',
    },
    hero: {
      line1: 'Your handstand.',
      line2: 'At your pace.',
      description: 'Strength, mobility and balance — step by step.',
      action: 'Explore programmes',
      imageAlt: 'A handstand against a dark background.',
    },
    programmes: {
      eyebrow: 'Ways to practise',
      title: 'Find your direction.',
      description: 'Build strength, explore mobility and make movement part of your day.',
      imageAlt: 'A person practising a seated mobility movement in a dark studio.',
    },
    method: {
      eyebrow: 'Method',
      title: 'Every step has a purpose.',
      description: 'From your starting point to your next step, with attention to your practice.',
      steps: [
        {
          title: 'Your starting point',
          body: 'Consider your experience, goals and questions before choosing a direction.',
        },
        {
          title: 'Consistent practice',
          body: 'Choose a structure for your sessions that you can return to.',
        },
        {
          title: 'Attention to progress',
          body: 'Notice changes and revisit the next steps in your practice.',
        },
      ],
    },
    coaching: {
      eyebrow: 'Ways to find support',
      title: 'Your practice. With support.',
      description: 'From an independent programme to a conversation and feedback from a coach.',
      compareLabel: 'Compare packages',
      bundleLabel: 'A programme and a personal conversation',
    },
    equipment: {
      eyebrow: 'Equipment',
      title: 'Make room for practice.',
      description: 'Equipment concepts for handstands, mobility and floor exercises.',
      imageAlt: 'Practice equipment: parallettes, a mat and blocks.',
    },
    future: {
      eyebrow: 'A future direction',
      title: 'More context for your practice.',
      body: 'We are planning a platform with training history, AI explanations and video analysis. These features are not yet available and are not included in this concept’s packages. Working with video will require separate consent.',
      items: ['Training log', 'AI explanations', 'Video analysis'],
    },
    faq: {
      eyebrow: 'Questions',
      title: 'Before you start.',
      items: [
        {
          id: 'start',
          question: 'Where should I start?',
          answer:
            'Explore the disciplines and consider what you want to work on. The proposed 1:1 consultation offers a way to discuss your goals and questions before choosing a programme.',
        },
        {
          id: 'mobility',
          question: 'Where does mobility fit in?',
          answer:
            'This discipline focuses on range of motion and movement control. The practice itself will depend on the programme you choose.',
        },
        {
          id: 'coaching',
          question: 'How does a programme differ from coaching?',
          answer:
            'A programme provides a structure for independent practice. Coaching adds feedback from a coach. Its format and frequency are still being defined.',
        },
        {
          id: 'platform',
          question: 'Are the training log and AI features available?',
          answer:
            'Not yet. A training log, AI explanations and video analysis are future directions for the platform. They are not available features of this concept.',
        },
      ],
    },
    footer: {
      title: 'Your next step.',
      action: 'Explore programmes',
      note: 'Studio concept. Programmes, package contents and availability are being defined.',
      top: 'Back to top',
    },
    common: {
      details: 'View details',
      close: 'Close',
      concept: 'Offer concept',
      included: 'The focus of this offer',
      offerNote:
        'This is a proposed format. Contents, access terms and support arrangements are still being defined.',
      equipmentNote:
        'Equipment concept. Models, specifications and availability are yet to be defined.',
      photoNote:
        'Images were generated for this concept. They do not depict the studio’s coach or serve as instructional demonstrations.',
    },
    offers: {
      handstand: {
        title: 'Handstand',
        summary: 'Support, body position and balance.',
        description:
          'Handstand practice with attention to support, body position and each next step.',
        includes: ['Hand support', 'Body position', 'Balance'],
      },
      mobility: {
        title: 'Strength & mobility',
        summary: 'Strength and control in motion.',
        description: 'Work on strength and movement control as part of your regular practice.',
        includes: ['Strength', 'Mobility', 'Movement control'],
      },
      flexibility: {
        title: 'Flexibility',
        summary: 'Explore your range without rushing.',
        description: 'Explore your range of motion without rushing or chasing difficult poses.',
        includes: ['Range of motion', 'Attention to how movement feels', 'Consistent practice'],
      },
      programme: {
        title: 'Programme',
        summary: 'One direction. Your own pace.',
        description: 'One chosen programme for a structured, independent practice.',
        includes: ['Your chosen programme', 'A structure for practice', 'An independent format'],
      },
      studio: {
        title: 'Studio',
        summary: 'More directions for your practice.',
        description:
          'A collection of programmes to bring different disciplines into your practice.',
        includes: ['A collection of programmes', 'Different disciplines', 'Independent practice'],
      },
      coach: {
        title: 'Coach+',
        summary: 'Practice with feedback.',
        description: 'Programmes with coach feedback to discuss your practice and next steps.',
        includes: ['Programmes', 'Coach feedback', 'Discussion of next steps'],
      },
      consultation: {
        title: '1:1 consultation',
        summary: 'Room for your questions.',
        description:
          'A conversation about your goals, experience and questions to help shape your practice.',
        includes: [
          'Goals and experience',
          'Questions about your practice',
          'A direction for further work',
        ],
      },
      bundle: {
        title: 'Programme + consultation',
        summary: 'Structure and a personal conversation.',
        description:
          'Independent practice and a dedicated conversation with a coach to explore your programme questions.',
        includes: ['Your chosen programme', 'A 1:1 consultation', 'Discussion of your questions'],
      },
      parallettes: {
        title: 'Parallettes',
        summary: 'Supports for your practice.',
        description:
          'A concept for supports used in handstand practice and strength work. A specific model has not yet been selected.',
        includes: ['Support work', 'Strength exercises'],
      },
      mat: {
        title: 'Practice mat',
        summary: 'Room to move.',
        description:
          'A mat concept for floor exercises. Materials, dimensions and package contents are still being defined.',
        includes: ['Floor practice', 'Mobility and flexibility'],
      },
      blocks: {
        title: 'Practice blocks',
        summary: 'Additional support.',
        description:
          'A block concept for selected mobility and flexibility exercises. The model and specifications are still being defined.',
        includes: ['Additional support', 'Mobility and flexibility'],
      },
    },
  },
} satisfies Record<Locale, SiteCopy>;
