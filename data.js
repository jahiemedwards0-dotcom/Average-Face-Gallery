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
    regionPolygon: [
      [19.85, -71.65], [19.80, -70.70], [19.30, -69.80], 
      [19.00, -70.00], [19.30, -71.00], [19.50, -71.70]
    ],
    category: "Phenotype",
    img: "images/cibaenid.jpeg",
    tags: [
      "Cibaenid",
      "Cibao",
      "Dominican Republic",
      "Tri-hybrid",
      "Endogamy",
      "Phenotype"
    ],
    sources: [
      { 
        label: "Moreno-Estrada et al. (2013) — Reconstructing the Population History of Puerto Rico and the Caribbean.", 
        url: "https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1003925" 
      },
      { 
        label: "Vardarajan et al. (2015) — Genetic Admixture in the Caribbean.", 
        url: "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4646764/" 
      }
    ],
    notes: `
      <p>
        The Cibaenid phenotype represents arguably the oldest stabilized tri-hybrid
        population in the post-contact Americas. This stability stems from early
        historical isolation and persistent regional endogamy in the Cibao Valley,
        where admixture began roughly two generations prior to comparable mainland
        populations.
      </p>
      <h3>Traits</h3>
      <ul>
        <li>
          <strong>Face:</strong> Morphology trends oval to slightly elongated, often
          appearing rounder due to neotonic tendencies stemming from a relatively
          short midface. Sexual dimorphism is marked: males often show robust
          mandibular structure, while females exhibit more tapered lower faces.
        </li>
        <li>
          <strong>Nose:</strong> Nasal breadth centers on a mesorrhine range,
          uniquely characterized by thin bridges opening to relatively broader bases.
          Profiles are generally straight, shifting into a subtle downturn toward
          the tip; less commonly, a very mild convexity is present.
        </li>
        <li>
          <strong>Hair:</strong> Texture falls in a straight to loose-curl range,
          typically dark but sometimes light brown.
        </li>
        <li>
          <strong>Pigmentation:</strong> Skin tone consistently trends warm-toned
          within a fair-to-light-medium brown spectrum. Though predominantly dark-eyed,
          light pigmentation variants—specifically hazel and green—occur in a
          minority of the sample.
        </li>
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
    regionPolygon: [
      [18.25, -67.05], [18.25, -66.50], [18.05, -66.50], [18.05, -67.05]
    ],
    category: "Phenotype",
    img: "images/indiera.jpeg",
    tags: [
      "Indiera",
      "Puerto Rico",
      "Cordillera Central",
      "Indigenous-shifted",
      "Boricua",
      "Phenotype"
    ],
    sources: [
      { 
        label: "User composite & regional phenotypic notes", 
        url: "" 
      }
    ],
    notes: `
      <p>
        The Indiera phenotype corresponds to the Indigenous-shifted population cluster
        concentrated in the "Indiera" barrios of Puerto Rico's Cordillera Central.
        While the island average often leans European, this regional variant represents
        a distinct phenotype that aligns with the area’s history as a refuge
        ("Place of the Indians").
      </p>
      <p>
        The face is typically defined by broad, high cheekbones (malar projection)
        paired with a sharp, robust jawline. Due to reduced orbital depth, the eyes
        often appear forward-set beneath a thick, low brow. Eye shape tends to be
        ovoid, frequently showing hooded upper lids or a subtle epicanthic fold.
      </p>
      <p>
        Skin tones are generally deep—often described as <em>canela</em> or bronze
        with a reddish cast. The nose is usually broad with a rounded, fleshy tip,
        and hair texture is predominantly straight to wavy, distinguishing it
        from other local variations.
      </p>
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
    regionPolygon: [
      [42.0, -124.0], [42.0, -109.0], [36.0, -103.0], [32.0, -94.0], 
      [26.0, -97.0], [22.0, -98.0], [20.0, -105.0], [23.0, -110.0], [32.0, -117.0]
    ],
    category: "Phenotype",
    img: "images/sinaloid.jpg",
    tags: [
      "Sinaloid",
      "Mexico & Central America Mestizo",
      "NW Mexico",
      "ranching",
      "mining",
      "regional variant"
    ],
    sources: [
      { label: "User composite & notes", url: "" }
    ],
    notes: `
      <h3>Description</h3>
      <p>
        A regional variant within the broader Mexico and Central America–Mestizo
        complex. It developed in the ranching–mining belt of northwest and
        north-central Mexico through long-term Spanish–Indigenous admixture.
      </p>
      <h3>Traits</h3>
      <ul>
        <li>Skin light- to medium-brown, tanning deeply; stature average to tall with a compact, stockier build.</li>
        <li>Faces often rounder in men and slightly longer in women; mild neoteny (soft, baby-faced look) is common.</li>
        <li>Nose medium and usually projecting; lips full.</li>
        <li>Eyes predominantly dark and slightly upturned; lighter shades appear in a minority; occasional epicanthic folds.</li>
        <li>Hair dark brown to black; straight or wavy; curls not rare.</li>
      </ul>
    `
  }, 
  {
    id: "average_mormon_corridor",
    title: "Average Mormon Corridor (LDS pioneer-descended)",
    macro: "North America",
    country: "United States",
    region: "Mormon Corridor (Intermountain West — Utah-centered)",
    lat: 40.712,
    lng: -111.901,
    regionPolygon: [
      [44.0, -112.0], [44.0, -111.0], [41.0, -110.0], [33.0, -109.0], 
      [33.0, -112.0], [37.0, -115.0], [42.0, -114.0]
    ],
    category: "Average face",
    img: "images/avg_mormon.jpeg",
    tags: [
      "Mormon Corridor",
      "LDS",
      "Latter-day Saints",
      "Pioneer descendants",
      "Utah",
      "Intermountain West",
      "Average face"
    ],
    sources: [
      {
        label: "The Church of Jesus Christ of Latter-day Saints — “Emigration”",
        url: "https://www.churchofjesuschrist.org/study/history/topics/emigration?lang=eng"
      },
      {
        label: "McLellan (1984) — “Genetic distances between the Utah Mormons and related populations”",
        url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC1684477/"
      }
    ],
    notes: `
      <p>
        This composite is presented as a Utah-centered “Mormon Corridor” (Intermountain West) average
        for LDS pioneer-descended white Americans. It is best understood as the demographic and kinship
        outcome of a historically specific conversion, migration, and settlement process: between 1840 and
        1890, large numbers of Latter-day Saint converts emigrated from Europe to the United States, with
        major source regions including the British Isles and Scandinavia, alongside smaller inputs from
        continental Europe.
      </p>
      <p>
        Genetically, “Utah Mormon / Utah European-descended” samples have long been discussed in human
        genetics as broadly Northern/Western European–affiliated rather than a sharply isolated population.
        Classic gene-frequency comparisons report Utah Mormon similarity to Northern European ancestors,
        consistent with a large founding population and ongoing gene flow.
      </p>
      <p>
        The facial pattern trends long-oval overall. The lower face often reads
        more square than tapered, with a sturdier jaw. Noses commonly read narrow, typically long and prominent. 
        Eye shape frequently falls in an almond-to-ovoid range, with mild upper-lid hooding appearing
        repeatedly in the portrait-heavy sample. Lip vermilion most often reads thin-to-medium.
      </p>
      <p>
        Pigmentation trends fair-to-light. Hair most commonly appears brown, with blond
        and (less often) reddish tones represented. Eye color variation includes blue/gray alongside hazel
        and brown. 
      </p>
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
    regionPolygon: [
      [-16.0, 176.5], [-16.0, 180.0], [-19.5, 180.0], [-19.5, 176.5]
    ],
    category: "Average face",
    img: "images/avg_fijian.jpg", 
    tags: ["Fiji", "iTaukei", "Melanesian","Polynesian", "Average face"],
    sources: [
      { label: "Based on classic and modern anthropological descriptions of iTaukei Fijians and Melanesians (Davis 1870; Flower 1879; Bellwood 1975; Spriggs 1997; Kong 2007; IGNOU Unit 2).", url: "" }
    ],
    notes: `
      <p>
        On average, their skin falls in a medium to deep brown range. The face is
        short and broad, with a big, strong jaw. The nose is medium in length but
        wide, with a round and sometimes bulbous tip. The lips are very full,
        especially the lower lip, and the brow and midface are slightly prominent.
      </p>
      <p>
        Hair is usually black and coily to tightly curled, though some people have
        looser curls or a reddish-brown tone, and a small minority naturally have
        lighter or blondish hair. The eyes are large and almond-shaped, almost
        always dark brown to nearly black. A faint epicanthic fold can also appear in some individuals.
        Body hair is abundant, and they are typically very robust and tall.
      </p>
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
    regionPolygon: [
      [35.5, -120.0], [35.5, -116.0], [34.0, -114.5], [32.5, -114.5], 
      [32.5, -117.2], [33.5, -118.5], [34.5, -120.5]
    ],
    category: "Average face",
    img: "images/avg_socalwasian.jpeg",
    tags: ["Wasian", "White–Asian", "Hapa", "Southern California", "Average face"],
    sources: [
      {
        label: "User composite of Southern California White–East Asian mixed faces.",
        url: ""
      }
    ],
    notes: `
      <p>
        This morph represents an average White–East Asian (Wasian) type drawn
        from Southern California. Skin tones typically fall in a very light to
        light beige or light olive range, often with a neutral or slightly warm
        undertone.
      </p>
      <p>
        Faces are usually oval to softly heart-shaped, with a round lower face and
        medium cheekbone prominence. The nose is moderate in bridge height (neither flat nor very high), 
        with a narrow-to-medium base and a rounded tip; 
        it often reads slightly more “European” in bridge but softer in the tip and nostrils.
        Lips are medium to medium-full, with a defined Cupid’s bow and a fuller lower lip. 
      </p>
      <p>
        Eyes are most often brown, with lighter shades also common; lid
        shapes range from full double-crease lids to softer lids with a faint or
        partial epicanthic fold. Hair is usually dark brown to black and straight
        to softly wavy. Overall, the look sits midway between local White American
        and East Asian averages, with a wide range of individual variation.
      </p>
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
    regionPolygon: [
      [-21.8, -66.3], [-21.8, -62.5], [-28.0, -62.0], 
      [-30.0, -65.0], [-28.0, -69.0], [-23.0, -67.0]
    ],
    category: "Average face",
    img: "images/avg_northwest_argentine.jpg",
    tags: ["Argentina", "Northwest Argentina", "Average face"],
    sources: [
      { label: "Average Northwest Argentine morph", url: "" }
    ],
    notes: `
      <p>
        On average, skin sits in a light to medium brown / light olive-tan range,
        often with warm or slightly ruddy undertones. The face is oval to compact
        and can run a bit long, with medium to high cheekbones and a tapered jaw
        ending in a rounded chin.
      </p>
      <p>
        The nose is mostly mesorrhine, with a straight to slightly arched bridge,
        moderate bridge height, and a rounded tip; in many people it reads as a
        fairly long, projecting nose in profile. Brows tend to be thick and
        relatively straight, and the eyes are almond-shaped, set fairly
        horizontally, sometimes with a faint inner fold or slightly fuller upper
        lids.
      </p>
      <p>
        Hair is usually dark brown to black, most often straight to lightly wavy.
        DNA is typically Indigenous-leaning, averaging 58% on average in the region.
      </p>
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
    regionPolygon: [
      [35.0, 69.0], [35.0, 72.0], [30.0, 70.0], 
      [29.0, 66.0], [31.0, 61.0], [33.0, 62.0], [34.0, 67.0]
    ],
    category: "Average face",
    img: "images/avg_afghan_pashtun.jpg",
    tags: ["Afghan","Pashtun","Average face"],
    sources: [
      {label:"Average Afghan Pashtun morph", url: ""}
    ],
    notes: `
      <p>
        National / regional facial average morph for Pashtun populations across
        Afghanistan and Pakistan. Detailed trait write-up to be added later.
      </p>
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
    regionPolygon: [
      [36.0, 70.0], [36.2, 71.5], [35.0, 71.5], [34.8, 70.0]
    ],
    category: "Average face",
    img: "images/avg_nuristani.jpeg",
    tags: ["Nuristani", "Afghanistan", "Hindu Kush", "Average face"],
    sources: [
      { label: "Encyclopaedia Iranica — “AFGHANISTAN iv. Ethnography.”", url: "" },
      { label: "Ayub et al. 2015 (AJHG) — “The Kalash Genetic Isolate.”", url: "" }
    ],
    notes: `
      <p>
        This average represents Nuristanis from the remote highlands of eastern
        Afghanistan. Faces tend to be longer and narrower on average, with
        very fair to medium-brown skin and hair that ranges from blond to dark
        brown, often wavy. Mixed or light eye colors appear at notable rates
        compared to surrounding regions.
      </p>
      <p>
        The nose is typically long and prominent, with a fleshy bridge and a
        straight to aquiline profile. The upper face often shows strong brow
        ridges, deep-set eyes, and thick, well-shaped eyebrows.
      </p>
      <p>
        Local legend sometimes links Nuristanis to Alexander-era Greek ancestry,
        but genetic studies do not support a recent Greek origin. The best
        current view places Nuristanis within Indo-Iranian and broader Hindu
        Kush populations, shaped by long-term geographic isolation.
      </p>
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
    regionPolygon: [
      [-2.0, -44.0], [-5.0, -35.0], [-10.0, -36.0], 
      [-18.0, -39.0], [-18.0, -42.0], [-10.0, -42.0], [-2.0, -46.0]
    ],
    category: "Average face",
    img: "images/avg_mulato_brazil.jpeg",
    tags: ["Brazil", "Mulato", "Pardo", "Afro-European", "Average face"],
    sources: [
      {
        label: "Historical and demographic work on Brazilian 'mulato' / 'pardo' populations and coastal mixed communities.",
        url: ""
      }
    ],
    notes: `
      <p>
        This average represents colonial-era mulato Brazilians: populations formed
        largely from African-descended women and European-descended men, sometimes
        with additional Indigenous ancestry. Historically they were concentrated in
        the North and Northeast and along major coastal towns and cities.
      </p>
      <p>
        On average, skin tones range from light brown to medium-dark brown, often
        with warm golden or slightly reddish undertones. Faces are usually oval to
        slightly long, with visible but not extreme cheekbones and a tapered jaw.
        The nose tends to be medium in width with a straight to slightly convex
        bridge and a rounded, fleshy tip. Lips are medium to full.
      </p>
      <p>
        Hair is typically dark brown to black and wavy to curly, though tighter
        coils also occur. Eyes are mostly dark brown, with some light-brown or
        hazel examples. As with any mixed population, there is a wide range of
        individual variation around this average.
      </p>
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
    regionPolygon: [
      [13.35, -59.65], [13.35, -59.50], [13.05, -59.45], [13.05, -59.60]
    ],
    category: "Average face",
    img: "images/avg_afrobajan.jpeg",
    tags: ["Barbados", "Afro-Bajan", "Caribbean", "Average face"],
    sources: [
      {
        label: "Murray T. et al. (2010). African and non-African admixture components in African Americans and an African Caribbean population. Genet Epidemiol 34(6):561–568.",
        url: ""
      }
    ],
    notes: `
      <p>
        This average represents Afro-Bajans, the majority Black population of Barbados,
        shaped by nearly four centuries of African-descended continuity on the island.
        Skin typically falls in a medium- to dark-brown range with warm or slightly
        reddish undertones. Faces are usually oval to softly rounded, with noticeable
        soft-tissue fullness in the cheeks and a gently tapered jaw.
      </p>
      <p>
        The nose is generally broad with a fleshy to narrow tip, and the
        nostrils flare moderately. Eyes are dark brown, often with a visible upper-lid
        crease and mild lid hooding rather than deep-set sockets. Lips are full, and
        hair is tightly curled to coily, most often in the 3C–4C range. As with any
        population average, individual Afro-Bajans span a wide range around this central
        pattern. Afro-Bajans average around ~87% African, and ~13% European.
      </p>
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
    regionPolygon: [
      [55.0, 70.0], [50.0, 87.0], [42.0, 80.0], [41.0, 68.0], 
      [45.0, 55.0], [51.0, 46.0], [54.0, 60.0]
    ],
    category: "Average face",
    img: "images/avg_kazakh.jpeg",
    tags: ["Kazakh", "Central Asia", "Eurasian", "Average face"],
    sources: [
      {
        label: "Bidzhanov, D. et al. – External nose anthropometry in ethnic Kazakhs (nasal index, bridge height).",
        url: ""
      }
    ],
    notes: `
      <p>
        Ethnic Kazakhs, on average, show an intermediate Eurasian look: mostly East Eurasian ancestry
        with a substantial West Eurasian component. Faces tend to broad and compact (brachycephalic), often medium to slightly long with very prominent
        cheekbones and a slightly convex profile.
      </p>
      <p>
        The nose is mildly leptorrhine to mesorrhine on average (moderate width relative to height; nasal index around 80), with a low to
        medium bridge and a rounded tip; some individuals show a mild dorsal hump. Eyes are
        almond-shaped, usually dark brown but sometimes lighter, with epicanthic folds common but often weaker than in
        East Asians. Skin tones range from light beige to light-brown/olive; hair is very dark (sometimes lighter), 
        and straight to slightly wavy, and men often grow fuller facial hair than typical
        East Asians.
      </p>
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
    regionPolygon: [
      [36.5, -94.0], [36.5, -76.0], [32.0, -80.0], [30.0, -82.0], 
      [29.0, -89.0], [29.5, -95.0], [33.0, -94.0]
    ],
    category: "Phenotype",
    img: "images/mississipid.jpg",
    tags: [
      "Mississipid",
      "African American",
      "Deep South",
      "Great Migration",
      "Phenotype"
    ],
    sources: [
      { label: "User composite & notes", url: "" }
    ],
    notes: `
      <h3>Description</h3>
      <p>
        Mississipid is an African American phenotype that developed in the
        plantation South of the United States. From the Deep South, this pattern
        spread into the Great Lakes region, the East Coast corridor, and the West
        Coast during the Great Migration. It is one of the most common phenotypic
        patterns among African Americans today, especially in urban centers,
        church-based communities, and multi-generation Southern families.
      </p>
      <h3>Traits</h3>
      <ul>
        <li>Medium-to-dark brown skin with warm or reddish undertones.</li>
        <li>Face usually round or oval; nose typically medium-broad.</li>
        <li>Lips full; jawline tapered rather than boxy.</li>
        <li>Eyes predominantly dark brown, with hazel appearing randomly in some individuals; medium-set with slightly hooded lids and, on rare occasions, faint epicanthic folds.</li>
        <li>Hair texture most often ranges from tight coils to looser curls (roughly 4C to 3C).</li>
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
    regionPolygon: [
      [39.7, -77.5], [39.8, -75.5], [38.5, -75.0], 
      [36.5, -75.8], [36.5, -78.0], [38.0, -78.5]
    ],
    category: "Phenotype",
    img: "images/chesapeakid.jpg.JPEG",
    tags: [
      "Chesapeakid",
      "African American",
      "Free people of color",
      "Chesapeake",
      "Mid-Atlantic",
      "Phenotype"
    ],
    sources: [
      { label: "Berlin, Ira. Slaves Without Masters: The Free Negro in the Antebellum South (1974).", url: "" }
    ],
    notes: `
      <h3>Description</h3>
      <p>
        Chesapeakid is a Black / African American phenotype that developed in the
        Chesapeake Bay region during the slave era. It grew out of one of the
        earliest and longest-lasting free people of color communities in the
        United States. Before Jim Crow
        and the one-drop rule, many people in this group were legally and socially
        classified as “mulatto” and stood out as distinct from both Black and
        white populations.
      </p>
      <p>
        During the twentieth-century Great Migration, Black migrants from the
        Deep South moved into Mid-Atlantic and industrial Northern cities. As a
        result, older Chesapeakid lineages now overlap and blend with Mississippid
        types in places such as Philadelphia, Baltimore, Washington, D.C., and
        parts of the Great Lakes region.
      </p>
      <h3>Traits</h3>
      <ul>
        <li>Faces medium in size and softly oval.</li>
        <li>Noses usually medium-wide, with a straight to slightly convex bridge, a rounded tip, and mild nostril flare.</li>
        <li>Lips very full; jawline tends to be rounder or squarer than in Mississippid types.</li>
        <li>Eyes almond-shaped and predominantly dark brown, with occasional light-brown or hazel shades.</li>
        <li>Skin ranges from light brown to dark brown, usually with warm or golden undertones; freckles sometimes appear.</li>
        <li>Hair curly to tightly coily, typically ranging from 3A to 4C; body hair moderate to heavy.</li>
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
    regionPolygon: [
      [76.0, 110.0], [72.0, 160.0], [56.0, 138.0], [56.0, 116.0], [60.0, 106.0]
    ],
    category: "Average face",
    img: "images/avg_yakut.jpg",
    tags: ["Yakut", "Sakha Republic", "Russia", "Average face"],
    sources: [
      { label: "Average Yakut morph", url: "" }
    ],
    notes: `
      <p>
        The head is mainly rounded, with a short, very broad, relatively flat face
        and prominent cheekbones. The skin is light to medium yellow-brown; very
        dark complexions are rare. Hair is usually black, with dark to medium brown
        also seen; it is straight and coarse, and beard or body hair is sparse.
        Eyes are mostly dark brown to nearly black, though medium brown and
        occasional hazel-like tones also appear.
      </p>
      <p>
        The eyes are slightly up-slanted, and monolids or low creases are common.
        The nose is short to medium, usually straight to slightly concave, sometimes
        with a somewhat higher bridge or small convexity.
      </p>
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
    regionPolygon: [
      [55.8, -2.0], [54.0, -0.0], [52.8, 1.8], [51.3, 1.4], [51.0, 1.0], 
      [50.7, 0.0], [50.6, -2.5], [49.9, -5.3], [51.2, -4.2], [51.5, -2.6], 
      [53.4, -3.1], [54.5, -3.6]
    ],
    category: "Average face",
    img: "images/avg_english.jpg",
    tags: ["English","UK","Average face"],
    sources: [
      {label:"Average English morph", url: ""}
    ],
    notes: `
      <p>
        National facial average morph for England. A general reference for common
        English facial proportions and soft-tissue features; detailed phenotype
        write-up to be added later.
      </p>
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
    regionPolygon: [
      [55.3, -7.3], [54.0, -6.0], [52.2, -6.3], 
      [51.4, -9.5], [53.4, -10.2], [54.2, -10.0]
    ],
    category: "Average face",
    img: "images/avg_irish.jpg",
    tags: ["Irish","Ireland","Average face"],
    sources: [
      {label:"Average Irish morph", url: ""}
    ],
    notes: `
      <p>
        National facial average morph for Ireland, representing an aggregate of
        Irish faces. Detailed trait description will be added later.
      </p>
    `
  },
  {
    id: "averagebengali_bd",
    title: "Average Bengali (Bangladesh)",
    macro: "South Asia",
    country: "Bangladesh",
    region: "Bangladesh",
    lat: 23.685,
    lng: 90.356,
    regionPolygon: [
      [26.6, 88.0], [26.0, 89.8], [25.2, 92.8], [23.5, 92.2], 
      [21.0, 92.2], [21.6, 89.0], [22.6, 88.8], [24.5, 88.0]
    ],
    category: "Average face",
    img: "images/avg_bengali.jpg",
    tags: ["Bangladesh","Bengali","Average face"],
    sources: [
      {label:"Average Bengali morph (Bangladesh)", url: ""}
    ],
    notes: `
      <p>
        Bengalis of Bangladesh often have broad, round faces, though more angular
        shapes are also common. The nose is usually medium in size and slightly
        wide, with a straight to gently convex bridge.
      </p>
      <p>
        Skin tones range from light brown to deep medium brown, and hair is
        generally straight to very wavy and dark in color. Lips tend to be medium
        to full. The eyes are usually dark brown—lighter shades are uncommon—and
        some individuals may have a faint inner eye fold, high cheekbones, or
        features that lean toward an East Eurasian appearance.
      </p>
    `
  }
];
