// data.js – all morphs / averages live here
window.MORPHS = [
  {
    id: "cibaenid",
    title: "Cibaenid (Dominican Republic)",
    macro: "Caribbean",
    country: "Dominican Republic",
    region: "Cibao Valley (Santiago, La Vega, Moca)",
    lat: 19.3333,
    lng: -70.5333,
    category: "Phenotype",
    img: "images/cibaenid.jpeg",
    tags: ["Cibaenid", "Cibao", "Dominican Republic", "Tri-hybrid", "Endogamy", "Phenotype"],
    sources: [
      { label: "Moreno-Estrada et al. (2013) — Reconstructing the Population History of Puerto Rico and the Caribbean.", url: "https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1003925" },
      { label: "Vardarajan et al. (2015) — Genetic Admixture in the Caribbean.", url: "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4646764/" }
    ],
    notes: `
      <p>The Cibaenid phenotype represents arguably the oldest stabilized tri-hybrid population in the post-contact Americas. This stability stems from early historical isolation and persistent regional endogamy in the Cibao Valley, where admixture began roughly two generations prior to comparable mainland populations.</p>
      <h3>Traits</h3>
      <ul>
        <li><strong>Face:</strong> Morphology trends oval to slightly elongated...</li>
        <li><strong>Nose:</strong> Nasal breadth centers on a mesorrhine range...</li>
        <li><strong>Hair:</strong> Texture falls in a straight to loose-curl range...</li>
        <li><strong>Pigmentation:</strong> Skin tone consistently trends warm-toned...</li>
      </ul>
    `
  },
  {
    id: "indiera",
    title: "Indiera (Puerto Rico)",
    macro: "Caribbean",
    country: "Puerto Rico",
    region: "Cordillera Central (Indiera barrios)",
    lat: 18.169,
    lng: -66.944,
    category: "Phenotype",
    img: "images/indiera.jpeg",
    tags: ["Indiera", "Puerto Rico", "Cordillera Central", "Indigenous-shifted", "Boricua", "Phenotype"],
    sources: [
      { label: "User composite & regional phenotypic notes", url: "" }
    ],
    notes: `
      <p>The Indiera phenotype corresponds to the Indigenous-shifted population cluster concentrated in the "Indiera" barrios...</p>
      <p>The face is typically defined by broad, high cheekbones (malar projection) paired with a sharp, robust jawline...</p>
      <p>Skin tones are generally deep—often described as <em>canela</em> or bronze with a reddish cast...</p>
    `
  },
  {
    id: "sinaloid",
    title: "Sinaloid",
    macro: "Latin America",
    country: "Mexico",
    region: "Northwest & North-Central Mexico",
    lat: 25.172,
    lng: -107.479,
    // Here is the new polygon drawing the rough shape from your image
    regionPolygon: [
      [42.0, -124.0], // Northern CA
      [42.0, -109.0], // UT/WY border
      [36.0, -103.0], // NM/OK border
      [32.0, -94.0],  // East Texas
      [26.0, -97.0],  // South Texas
      [22.0, -98.0],  // Central Mexico East
      [20.0, -105.0], // Central Mexico West
      [23.0, -110.0], // Baja Tip
      [32.0, -117.0]  // SD/TJ border
    ],
    category: "Phenotype",
    img: "images/sinaloid.jpg",
    tags: ["Sinaloid", "Mexico & Central America Mestizo", "NW Mexico", "ranching", "mining", "regional variant"],
    sources: [
      { label: "User composite & notes", url: "" }
    ],
    notes: `
      <h3>Description</h3>
      <p>A regional variant within the broader Mexico and Central America–Mestizo complex. It developed in the ranching–mining belt of northwest and north-central Mexico through long-term Spanish–Indigenous admixture.</p>
      <h3>Traits</h3>
      <ul>
        <li>Skin light- to medium-brown, tanning deeply; stature average to tall with a compact, stockier build.</li>
        <li>Faces often rounder in men and slightly longer in women; mild neoteny (soft, baby-faced look) is common.</li>
        <li>Nose medium and usually projecting; lips full.</li>
        <li>Eyes predominantly dark and slightly upturned; lighter shades appear in a minority; occasional epicanthic folds.</li>
        <li>Hair dark brown to black; straight or wavy; curls not rare.</li>
      </ul>
  `,
  }, 
 {
  id: "average_mormon_corridor",
  title: "Average Mormon Corridor (LDS pioneer-descended)",
  macro: "North America",
  country: "United States",
  region: "Mormon Corridor (Intermountain West — Utah-centered)",
  lat: 40.712,
  lng: -111.901,
  category: "Average face",
  img: "images/avg_mormon.jpeg",
  tags: ["Mormon Corridor", "LDS", "Latter-day Saints", "Pioneer descendants", "Utah", "Intermountain West", "Average face"],
  sources: [
    { label: "The Church of Jesus Christ of Latter-day Saints...", url: "https://www.churchofjesuschrist.org/study/history/topics/emigration?lang=eng" }
  ],
  notes: `
    <p>This composite is presented as a Utah-centered “Mormon Corridor” (Intermountain West) average...</p>
    <p>Genetically, “Utah Mormon / Utah European-descended” samples have long been discussed in human genetics...</p>
    <p>The facial pattern trends long-oval overall...</p>
    <p>Pigmentation trends fair-to-light...</p>
  `
},
{
  id: "averagefijian_itaukei",
  title: "Average iTaukei Fijian",
  macro: "Oceania",
  country: "Fiji",
  region: "Fiji",
  lat: -17.713,
  lng: 178.065,
  category: "Average face",
  img: "images/avg_fijian.jpg", 
  tags: ["Fiji", "iTaukei", "Melanesian","Polynesian", "Average face"],
  sources: [
    { label: "Based on classic and modern anthropological descriptions...", url: "" }
  ],
  notes: `
    <p>On average, their skin falls in a medium to deep brown range...</p>
    <p>Hair is usually black and coily to tightly curled...</p>
  `
},
 {
  id: "average_socalwasian",
  title: "Average SoCal Wasian",
  macro: "North America",
  country: "United States",
  region: "Southern California",
  lat: 34.052,
  lng: -118.243,
  category: "Average face",
  img: "images/avg_socalwasian.jpeg",
  tags: ["Wasian", "White–Asian", "Hapa", "Southern California", "Average face"],
  sources: [
    { label: "User composite of Southern California White–East Asian mixed faces.", url: "" }
  ],
  notes: `
    <p>This morph represents an average White–East Asian (Wasian) type drawn from Southern California...</p>
    <p>Faces are usually oval to softly heart-shaped...</p>
    <p>Eyes are most often brown...</p>
  `
},
  {
    id: "average_northwest_argentine",
    title: "Average Northwest Argentine",
    macro: "Latin America",
    country: "Argentina",
    region: "Northwest Argentina",
    lat: -24.782,
    lng: -65.423,
    category: "Average face",
    img: "images/avg_northwest_argentine.jpg",
    tags: ["Argentina", "Northwest Argentina", "Average face"],
    sources: [
      { label: "Average Northwest Argentine morph", url: "" }
    ],
    notes: `
      <p>On average, skin sits in a light to medium brown...</p>
      <p>The nose is mostly mesorrhine...</p>
      <p>Hair is usually dark brown to black...</p>
    `
  },
  {
    id: "averagepashtun",
    title: "Average Afghan Pashtun",
    macro: "South-Central Asia",
    country: "Afghanistan / Pakistan",
    region: "Pashtun belt",
    lat: 33.000,
    lng: 69.000,
    category: "Average face",
    img: "images/avg_afghan_pashtun.jpg",
    tags: ["Afghan","Pashtun","Average face"],
    sources: [
      {label:"Average Afghan Pashtun morph", url: ""}
    ],
    notes: `
      <p>National / regional facial average morph for Pashtun populations across Afghanistan and Pakistan.</p>
    `
  },
 {
    id: "average_nuristani",
    title: "Average Nuristani",
    macro: "South-Central Asia",
    country: "Afghanistan",
    region: "Nuristan (eastern Hindu Kush)",
    lat: 35.321,
    lng: 70.835,
    category: "Average face",
    img: "images/avg_nuristani.jpeg",
    tags: ["Nuristani", "Afghanistan", "Hindu Kush", "Average face"],
    sources: [
      { label: "Encyclopaedia Iranica — “AFGHANISTAN iv. Ethnography.”", url: "" }
    ],
    notes: `
      <p>This average represents Nuristanis from the remote highlands...</p>
      <p>The nose is typically long and prominent...</p>
      <p>Local legend sometimes links Nuristanis to Alexander-era Greek ancestry...</p>
    `
  },
{
  id: "averagemulato_brazil",
  title: "Average Mulato Brazilian",
  macro: "Latin America",
  country: "Brazil",
  region: "North & Northeast / coastal Brazil",
  lat: -12.971,
  lng: -38.510,
  category: "Average face",
  img: "images/avg_mulato_brazil.jpeg",
  tags: ["Brazil", "Mulato", "Pardo", "Afro-European", "Average face"],
  sources: [
    { label: "Historical and demographic work on Brazilian 'mulato'...", url: "" }
  ],
  notes: `
    <p>This average represents colonial-era mulato Brazilians...</p>
    <p>On average, skin tones range from light brown to medium-dark brown...</p>
    <p>Hair is typically dark brown to black and wavy to curly...</p>
  `
},
  {
  id: "average_afrobajan",
  title: "Average Afro-Bajan",
  macro: "Caribbean",
  country: "Barbados",
  region: "Barbados",
  lat: 13.193,
  lng: -59.543,
  category: "Average face",
  img: "images/avg_afrobajan.jpeg",
  tags: ["Barbados", "Afro-Bajan", "Caribbean", "Average face"],
  sources: [
    { label: "Murray T. et al. (2010).", url: "" }
  ],
  notes: `
    <p>This average represents Afro-Bajans, the majority Black population of Barbados...</p>
    <p>The nose is generally broad with a fleshy to narrow tip...</p>
  `
},
  {
  id: "averagekazakh",
  title: "Average Kazakh",
  macro: "Central Asia",
  country: "Kazakhstan",
  region: "Kazakhstan (ethnic Kazakhs)",
  lat: 48.019,
  lng: 66.923,
  category: "Average face",
  img: "images/avg_kazakh.jpeg",
  tags: ["Kazakh", "Central Asia", "Eurasian", "Average face"],
  sources: [
    { label: "Bidzhanov, D. et al...", url: "" }
  ],
  notes: `
    <p>Ethnic Kazakhs, on average, show an intermediate Eurasian look...</p>
    <p>The nose is mildly leptorrhine to mesorrhine on average...</p>
  `
},
  {
    id: "mississipid",
    title: "Mississipid (African American phenotype)",
    macro: "North America",
    country: "United States",
    region: "Deep South & Great Migration corridors",
    lat: 32.354,
    lng: -89.398,
    category: "Phenotype",
    img: "images/mississipid.jpg",
    tags: ["Mississipid", "African American", "Deep South", "Great Migration", "Phenotype"],
    sources: [
      { label: "User composite & notes", url: "" }
    ],
    notes: `
      <h3>Description</h3>
      <p>Mississipid is an African American phenotype that developed in the plantation South...</p>
      <h3>Traits</h3>
      <ul>
        <li>Medium-to-dark brown skin with warm or reddish undertones.</li>
        <li>Face usually round or oval; nose typically medium-broad.</li>
        <li>Lips full; jawline tapered rather than boxy.</li>
        <li>Eyes predominantly dark brown...</li>
        <li>Hair texture most often ranges from tight coils to looser curls...</li>
      </ul>
    `
  },
  {
    id: "chesapeakid",
    title: "Chesapeakid (African American phenotype)",
    macro: "North America",
    country: "United States",
    region: "Chesapeake Bay region",
    lat: 38.258,
    lng: -76.084,
    category: "Phenotype",
    img: "images/chesapeakid.jpg.JPEG",
    tags: ["Chesapeakid", "African American", "Free people of color", "Chesapeake", "Mid-Atlantic", "Phenotype"],
    sources: [
      { label: "Berlin, Ira. Slaves Without Masters...", url: "" }
    ],
    notes: `
      <h3>Description</h3>
      <p>Chesapeakid is a Black / African American phenotype that developed in the Chesapeake Bay region...</p>
      <p>During the twentieth-century Great Migration, Black migrants from the Deep South moved...</p>
      <h3>Traits</h3>
      <ul>
        <li>Faces medium in size and softly oval.</li>
        <li>Noses usually medium-wide...</li>
        <li>Lips very full; jawline tends to be rounder...</li>
        <li>Eyes almond-shaped...</li>
        <li>Skin ranges from light brown to dark brown...</li>
        <li>Hair curly to tightly coily...</li>
      </ul>
    `
  },
  {
    id: "averageyakut",
    title: "Average Yakut",
    macro: "North Asia",
    country: "Russia",
    region: "Sakha Republic (Yakutia)",
    lat: 62.035,
    lng: 129.733,
    category: "Average face",
    img: "images/avg_yakut.jpg",
    tags: ["Yakut", "Sakha Republic", "Russia", "Average face"],
    sources: [
      { label: "Average Yakut morph", url: "" }
    ],
    notes: `
      <p>The head is mainly rounded, with a short, very broad, relatively flat face...</p>
      <p>The eyes are slightly up-slanted...</p>
    `
  },
  {
    id: "averageenglish",
    title: "Average English",
    macro: "Europe",
    country: "United Kingdom",
    region: "England",
    lat: 52.355,
    lng: -1.174,
    category: "Average face",
    img: "images/avg_english.jpg",
    tags: ["English","UK","Average face"],
    sources: [
      {label:"Average English morph", url: ""}
    ],
    notes: `
      <p>National facial average morph for England...</p>
    `
  },
  {
    id: "averageirish",
    title: "Average Irish",
    macro: "Europe",
    country: "Ireland",
    region: "Ireland",
    lat: 53.142,
    lng: -7.692,
    category: "Average face",
    img: "images/avg_irish.jpg",
    tags: ["Irish","Ireland","Average face"],
    sources: [
      {label:"Average Irish morph", url: ""}
    ],
    notes: `
      <p>National facial average morph for Ireland...</p>
    `
  }
];
