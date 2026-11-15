export interface Review {
    id: string;
    author: string;
    date: string;
    comment: string;
}

export interface Lead {
    id: string;
    name: string;
    category: string;
    rating: number;
    reviewsCount: number;
    isSaved: boolean; // Controla si está en frío (false) o en "Mis prospectos" (true)
    status: 'Nuevo' | 'Pendiente' | 'Contactado' | 'En Negociación' | 'Cliente Cerrado' | 'Descartado';
    contactName?: string;
    email?: string | null;
    phone?: string | null;
    website?: string | null;
    lastActivity?: string;
    dealValue?: string;
    mainProblem: string;
    problemDescription: string;
    recentReviews: Review[];
    draftSubject: string;
    draftBody: string;
}

export const ALL_MOCK_LEADS: Lead[] = [
    {
        id: '1',
        name: 'Hotel Bella Vista',
        category: 'Alojamiento',
        rating: 2.5,
        reviewsCount: 45,
        isSaved: true, // Ya guardado en Mis Prospectos
        status: 'En Negociación',
        contactName: 'Roberto Gómez',
        email: 'roberto@bellavista.com',
        phone: '+52 985 123 4567',
        website: 'www.hotelbellavista.com',
        lastActivity: 'Hace 2 días',
        dealValue: '$299/mo',
        mainProblem: 'Atención en recepción',
        problemDescription: 'Múltiples quejas sobre tiempos de espera largos durante el check-in.',
        recentReviews: [
            { id: 'r1', author: 'María G.', date: '15 de ene. de 2026', comment: '“La habitación estaba limpia, pero tardaron 40 minutos en atendernos en recepción.”' },
            { id: 'r1b', author: 'Luis T.', date: '03 de feb. de 2026', comment: '“El personal de recepción parecía saturado y poco amable.”' }
        ],
        draftSubject: 'Oportunidad para agilizar la experiencia de huéspedes en Hotel Bella Vista',
        draftBody: 'Hola Roberto,\nEstuve revisando las reseñas recientes de Hotel Bella Vista y noté que varios huéspedes mencionan demoras en recepción. En RepuSense ayudamos a hoteles a gestionar su reputación y responder preventivamente. ¿Tienes 10 minutos esta semana para platicarlo?'
    },
    {
        id: '2',
        name: 'Los Pollos Hermanos',
        category: 'Restaurante',
        rating: 2.5,
        reviewsCount: 42,
        isSaved: false, // Lead en frío
        status: 'Nuevo',
        contactName: 'Gustavo F.',
        email: null,
        phone: null,
        website: 'www.lospollos.com',
        lastActivity: 'Sin actividad',
        mainProblem: 'Atención al cliente',
        problemDescription: 'Demoras y dificultades para recibir ayuda en horas pico.',
        recentReviews: [
            { id: 'r2', author: 'Jorge R.', date: '20 de oct. de 2026', comment: '“La comida está bien, pero tardaron mucho en traer la cuenta.”' }
        ],
        draftSubject: 'Una oportunidad para mejorar la atención en Los Pollos Hermanos',
        draftBody: 'Hola,\nHe estado revisando algunas reseñas recientes de su restaurante y noté que varios clientes mencionan demoras en horas pico. Me encantaría mostrarles cómo automatizar la gestión de opiniones.'
    },
    {
        id: '3',
        name: 'Northstar Hotel',
        category: 'Hoteles',
        rating: 2.4,
        reviewsCount: 82,
        isSaved: false, // Lead en frío
        status: 'Pendiente',
        email: 'contacto@northstar.com',
        phone: '+52 999 888 7766',
        website: 'www.northstarhotel.com',
        lastActivity: 'Sin actividad',
        mainProblem: 'Limpieza y mantenimiento',
        problemDescription: 'Reportes recurrentes sobre aire acondicionado y ruido.',
        recentReviews: [
            { id: 'r3', author: 'Pedro S.', date: '02 de nov. de 2026', comment: '“Buena ubicación pero el clima de la habitación hacía mucho ruido.”' }
        ],
        draftSubject: 'Mejora de reseñas para Northstar Hotel',
        draftBody: 'Hola,\nNotamos oportunidades clave para elevar su calificación en Google Maps atendiendo los comentarios de mantenimiento de habitaciones.'
    },
    {
        id: '4',
        name: 'Clínica Dental Sonrisas',
        category: 'Salud',
        rating: 2.8,
        reviewsCount: 112,
        isSaved: true, // Guardado - Cliente Cerrado
        status: 'Cliente Cerrado',
        contactName: 'Dra. Ana Silva',
        email: 'contacto@sonrisas.mx',
        phone: '+52 985 987 6543',
        website: 'www.sonrisas.mx',
        lastActivity: 'Hoy',
        dealValue: '$199/mo',
        mainProblem: 'Gestión de citas',
        problemDescription: 'Pacientes reportan empalme de horarios y falta de recordatorios.',
        recentReviews: [
            { id: 'r4', author: 'Laura P.', date: '10 de sep. de 2026', comment: '“Excelente doctora, pero mi cita empezó una hora tarde.”' }
        ],
        draftSubject: 'Mejora en la percepción de puntualidad para Clínica Dental Sonrisas',
        draftBody: 'Hola Dra. Ana,\nNotamos que sus pacientes valoran mucho su atención médica, aunque mencionan esperas en sala...'
    },
    {
        id: '5',
        name: 'Orbit Coffee',
        category: 'Cafeterías',
        rating: 3.1,
        reviewsCount: 29,
        isSaved: false, // Lead en frío (para probar calificación >= 3.0 en amarillo/ámbar)
        status: 'Nuevo',
        contactName: 'Sofía Méndez',
        email: 'hola@orbitcoffee.mx',
        phone: '+52 999 456 1230',
        website: null,
        lastActivity: 'Sin actividad',
        mainProblem: 'Consistencia en pedidos',
        problemDescription: 'Errores frecuentes en órdenes para llevar y temperatura de bebidas.',
        recentReviews: [
            { id: 'r5', author: 'Carlos D.', date: '28 de oct. de 2026', comment: '“El lugar es muy bonito pero pides leche deslactosada y te dan entera.”' },
            { id: 'r5b', author: 'Elena V.', date: '05 de nov. de 2026', comment: '“Café tibio y un poco caro para la porción.”' }
        ],
        draftSubject: 'Impulsa la calificación de Orbit Coffee a 4.5 estrellas',
        draftBody: 'Hola Sofía,\nNos encanta el concepto de Orbit Coffee, pero vimos algunas reseñas recientes sobre errores en pedidos para llevar que están bajando su promedio...'
    },
    {
        id: '6',
        name: 'Spherule Retail',
        category: 'Tiendas',
        rating: 2.2,
        reviewsCount: 66,
        isSaved: false, // Lead en frío
        status: 'Pendiente',
        email: null,
        phone: '+52 985 321 7890',
        website: 'www.spheruleretail.com',
        lastActivity: 'Sin actividad',
        mainProblem: 'Políticas de devolución',
        problemDescription: 'Clientes insatisfechos con el proceso de cambios en sucursal.',
        recentReviews: [
            { id: 'r6', author: 'Fernando M.', date: '12 de oct. de 2026', comment: '“Pésima actitud del gerente cuando quise cambiar una talla con ticket.”' }
        ],
        draftSubject: 'Estrategia de recuperación de clientes para Spherule Retail',
        draftBody: 'Hola,\nDetectamos un patrón en sus reseñas públicas respecto a cambios y devoluciones que podría estar frenando ventas recurrentes...'
    },
    {
        id: '7',
        name: 'Cafetería La Esquinita',
        category: 'Cafeterías',
        rating: 2.6,
        reviewsCount: 19,
        isSaved: true, // Guardado - Contactado
        status: 'Contactado',
        contactName: 'María López',
        email: 'laesquinita.cafe@gmail.com',
        phone: '+52 985 555 0192',
        website: null,
        lastActivity: 'Hace 4 días',
        dealValue: '$149/mo',
        mainProblem: 'Falta de respuesta a reseñas',
        problemDescription: 'Ninguna reseña negativa ha sido respondida en los últimos 6 meses.',
        recentReviews: [
            { id: 'r7', author: 'Andrés H.', date: '19 de ago. de 2026', comment: '“Los chilaquiles estaban fríos y nadie nos preguntó si todo estaba bien.”' }
        ],
        draftSubject: 'Seguimiento: Cómo responder y convertir reseñas críticas en La Esquinita',
        draftBody: 'Hola María,\nTal como platicamos por teléfono, te comparto el diagnóstico de las últimas reseñas de Cafetería La Esquinita...'
    },
    {
        id: '8',
        name: 'Estabilit Consultores',
        category: 'Consultora',
        rating: 2.9,
        reviewsCount: 14,
        isSaved: true, // Guardado - Nuevo (recién guardado por el vendedor)
        status: 'Nuevo',
        contactName: 'Lic. Javier Ruiz',
        email: 'jruiz@estabilit.com',
        phone: '+52 999 222 3344',
        website: 'www.estabilit.com',
        lastActivity: 'Guardado hoy',
        dealValue: '$399/mo',
        mainProblem: 'Comunicación post-servicio',
        problemDescription: 'Clientes reportan falta de seguimiento tras contratar asesorías.',
        recentReviews: [
            { id: 'r8', author: 'Martha C.', date: '01 de nov. de 2026', comment: '“Una vez que pagas el anticipo tardan días en contestar un correo.”' }
        ],
        draftSubject: 'Fortaleciendo la confianza digital de Estabilit Consultores',
        draftBody: 'Estimado Lic. Javier,\nEn el sector de consultoría B2B la reputación en Google es decisiva. Notamos un par de comentarios sobre tiempos de respuesta...'
    },
    {
        id: '9',
        name: 'Hacienda Los Arcos',
        category: 'Alojamiento',
        rating: 2.7,
        reviewsCount: 94,
        isSaved: false, // Lead en frío
        status: 'Nuevo',
        contactName: 'Alejandro Pech',
        email: 'reservas@haciendalosarcos.mx',
        phone: '+52 985 856 1122',
        website: 'www.haciendalosarcos.mx',
        lastActivity: 'Sin actividad',
        mainProblem: 'Conectividad Wi-Fi y alberca',
        problemDescription: 'Huéspedes señalan señal débil en habitaciones y mantenimiento de piscina.',
        recentReviews: [
            { id: 'r9', author: 'Sarah W.', date: '08 de nov. de 2026', comment: '“Hermoso lugar histórico, pero el Wi-Fi no llega a los cuartos y la alberca estaba turbia.”' }
        ],
        draftSubject: 'Oportunidad para destacar la experiencia histórica de Hacienda Los Arcos',
        draftBody: 'Hola Alejandro,\nLos viajeros aman la arquitectura de Hacienda Los Arcos, pero detalles operativos en sus reseñas están afectando su posicionamiento...'
    },
    {
        id: '10',
        name: 'Ferretería y Materiales El Constructor',
        category: 'Tiendas',
        rating: 2.3,
        reviewsCount: 37,
        isSaved: true, // Guardado - En Negociación
        status: 'En Negociación',
        contactName: 'Ing. Héctor Chan',
        email: 'ventas@elconstructor.mx',
        phone: null,
        website: null,
        lastActivity: 'Ayer',
        dealValue: '$249/mo',
        mainProblem: 'Tiempos de entrega a domicilio',
        problemDescription: 'Retrasos en fletes y falta de notificación al cliente.',
        recentReviews: [
            { id: 'r10', author: 'Roberto K.', date: '25 de oct. de 2026', comment: '“Prometieron entregar el material a las 10 am y llegaron a las 5 pm sin avisar.”' }
        ],
        draftSubject: 'Propuesta RepuSense para Ferretería El Constructor',
        draftBody: 'Hola Ing. Héctor,\nTe envío la propuesta formal para automatizar encuestas de satisfacción tras cada entrega de material...'
    },
    {
        id: '11',
        name: 'Tacos y Cortes Don Pepe',
        category: 'Restaurante',
        rating: 2.1,
        reviewsCount: 58,
        isSaved: true, // Guardado pero marcado como Descartado (aparecerá directo en /historial)
        status: 'Descartado',
        contactName: 'José Luis Pérez',
        email: 'donpepe.tacos@gmail.com',
        phone: '+52 985 111 2233',
        website: null,
        lastActivity: 'Hace 1 semana',
        mainProblem: 'Higiene y tiempo de entrega',
        problemDescription: 'Comentarios negativos sobre limpieza en mesas y demoras en servicio a domicilio.',
        recentReviews: [
            { id: 'r11', author: 'Diana M.', date: '14 de oct. de 2026', comment: '“Tardaron más de una hora en mandar la orden y llegó fría.”' }
        ],
        draftSubject: 'Mejora en tiempos de entrega y reputación para Tacos Don Pepe',
        draftBody: 'Hola José Luis,\nRevisamos las opiniones recientes de su restaurante y vimos una oportunidad clara para mejorar la percepción de sus entregas a domicilio...'
    },
    {
        id: '12',
        name: 'La Terraza del Parque',
        category: 'Restaurante',
        rating: 2.9,
        reviewsCount: 134,
        isSaved: false, // Lead en frío con alto volumen de reseñas (ideal para Dashboard)
        status: 'Nuevo',
        contactName: 'Valeria Ortiz',
        email: 'gerencia@laterrazaparque.mx',
        phone: '+52 999 777 8899',
        website: 'www.laterrazaparque.mx',
        lastActivity: 'Sin actividad',
        mainProblem: 'Atención de meseros',
        problemDescription: 'Turistas reportan descuido en el servicio y errores en el cobro de propinas.',
        recentReviews: [
            { id: 'r12', author: 'Mark T.', date: '09 de nov. de 2026', comment: '“La vista es increíble pero el mesero nos ignoró por 30 minutos.”' },
            { id: 'r12b', author: 'Camila S.', date: '11 de nov. de 2026', comment: '“Revisen bien su cuenta antes de pagar, nos agregaron bebidas de más.”' }
        ],
        draftSubject: 'Protege la reputación turística de La Terraza del Parque',
        draftBody: 'Hola Valeria,\nCon más de 130 reseñas, La Terraza del Parque es un punto de referencia, pero algunos comentarios recientes sobre el servicio están frenando su calificación...'
    },
    {
        id: '13',
        name: 'Spa & Bienestar Cenote Azul',
        category: 'Salud',
        rating: 3.2,
        reviewsCount: 31,
        isSaved: false, // Lead en frío (para probar calificación >= 3.0 en color ámbar)
        status: 'Pendiente',
        contactName: 'Lucía Mendoza',
        email: 'citas@cenoteazulspa.com',
        phone: null,
        website: 'www.cenoteazulspa.com',
        lastActivity: 'Sin actividad',
        mainProblem: 'Confirmación de reservaciones',
        problemDescription: 'Clientes llegan a su sesión y no encuentran registro de su cita agendada por WhatsApp.',
        recentReviews: [
            { id: 'r13', author: 'Fernanda G.', date: '04 de nov. de 2026', comment: '“Los masajes son excelentes, lástima que su recepción es un desorden con las citas.”' }
        ],
        draftSubject: 'Automatiza la satisfacción de tus clientes en Spa Cenote Azul',
        draftBody: 'Hola Lucía,\nNotamos que sus terapias tienen excelentes comentarios, pero la gestión de citas está generando reseñas de 2 y 3 estrellas...'
    },
    {
        id: '14',
        name: 'Boutique Artesanal Maya',
        category: 'Tiendas',
        rating: 2.6,
        reviewsCount: 22,
        isSaved: true, // Guardado - Contactado
        status: 'Contactado',
        contactName: 'Elena Uc',
        email: 'ventas@artesaniasmaya.mx',
        phone: '+52 985 444 5566',
        website: 'www.artesaniasmaya.mx',
        lastActivity: 'Ayer',
        dealValue: '$179/mo',
        mainProblem: 'Horarios desactualizados en Google',
        problemDescription: 'Clientes acuden en horarios marcados como abiertos y encuentran cerrado.',
        recentReviews: [
            { id: 'r14', author: 'David L.', date: '30 de oct. de 2026', comment: '“Caminamos 20 minutos porque en Google decía abierto hasta las 8 pm y cerraron a las 6.”' }
        ],
        draftSubject: 'Seguimiento: Optimización de perfil y reseñas para Boutique Artesanal Maya',
        draftBody: 'Hola Elena,\nUn gusto saludarte de nuevo. Te comparto cómo podemos mantener sincronizada su ficha de Google y responder a los visitantes...'
    },
    {
        id: '15',
        name: 'Café Colonial Centro',
        category: 'Cafeterías',
        rating: 2.4,
        reviewsCount: 75,
        isSaved: false, // Lead en frío
        status: 'Nuevo',
        contactName: 'Martín Solís',
        email: null,
        phone: '+52 999 333 1100',
        website: null,
        lastActivity: 'Sin actividad',
        mainProblem: 'Tiempo de espera en cocina',
        problemDescription: 'Demoras de hasta 45 minutos para desayunos sencillos en fines de semana.',
        recentReviews: [
            { id: 'r15', author: 'Patricia R.', date: '12 de nov. de 2026', comment: '“El café es rico, pero esperamos 50 minutos por unos huevos al gusto.”' }
        ],
        draftSubject: 'Convierte las visitas de fin de semana en reseñas de 5 estrellas en Café Colonial',
        draftBody: 'Hola Martín,\nEstuvimos analizando el flujo de opiniones de Café Colonial Centro y detectamos que los tiempos de espera en desayuno son su principal área de mejora...'
    }
];