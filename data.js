// data.js – all morphs / averages live here
window.MORPHS = [
  {
    id: "cibaenid",
    title: "Cibaenid (Dominican Republic)",
    macro: "Caribbean",
    country: "Dominican Republic",
    region: "Cibao Valley (Santiago, La Vega, Moca)",
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

      <img src="images/sinaloid-map.jpg"
           alt="Sinaloid map"
           style="display:block;width:100%;margin-top:10px;border-radius:12px;">
  `,
  }, 
 {
  id: "average_mormon_corridor",
  title: "Average Mormon Corridor (LDS pioneer-descended)",
  macro: "North America",
  country: "United States",
  region: "Mormon Corridor (Intermountain West — Utah-centered)",
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
      label:
        "The Church of Jesus Christ of Latter-day Saints — “Emigration” (1840–1890 totals; British Isles & Scandinavia major sources)",
      url: "https://www.churchofjesuschrist.org/study/history/topics/emigration?lang=eng"
    },
    {
      label:
        "McLellan (1984) — “Genetic distances between the Utah Mormons and related populations” (Human Biology; PMC full text)",
      url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC1684477/"
    },
    {
      label:
        "HapMap Phase 3 sample label CEU — “Utah residents with Northern and Western European ancestry (CEPH collection)” (Broad Institute)",
      url: "https://www.broadinstitute.org/medical-and-population-genetics/hapmap-3"
    },
    {
      label:
        "University of Utah / Huntsman Cancer Institute — Utah Population Database (UPDB) overview (deep pedigrees linked to demographic/medical data)",
      url: "https://uofuhealth.utah.edu/huntsman/utah-population-database"
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
      consistent with a large founding population and ongoing gene flow. In modern population genetics,
      the HapMap/CEPH “CEU” label is explicitly defined as Utah residents with Northern and Western
      European ancestry, underscoring why Utah-centered European-descent pedigrees are frequently used
      in research contexts.
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
  category: "Average face",
  img: "images/avg_fijian.jpg", // make sure this file exists
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
      Body hair is abundant, and they are 
      typically very robust and tall.
    </p>
  `
},
 {
  id: "average_socalwasian",
  title: "Average SoCal Wasian",
  macro: "North America",
  country: "United States",
  region: "Southern California",
  category: "Average face",
  img: "images/avg_socalwasian.jpeg", // change extension if needed
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
      Skin tone typically falls in a light-beige to light-tan range depending on parental background,
      and hair is usually dark brown to black, straight to wavy.
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
    category: "Average face",
    img: "images/avg_nuristani.jpeg",
    tags: ["Nuristani", "Afghanistan", "Hindu Kush", "Average face"],
    sources: [
      { label: "Encyclopaedia Iranica — “AFGHANISTAN iv. Ethnography.”", url: "" },
      { label: "Encyclopaedia Iranica — “NURESTÂNI LANGUAGES.”", url: "" },
      { label: "Ayub et al. 2015 (AJHG) — “The Kalash Genetic Isolate.”", url: "" },
      { label: "Cacopardo — “Are the Kalasha really of Greek origin?”", url: "" },
      { label: "Di Cristofaro et al. 2013 (PLOS ONE) — Afghan population genetics.", url: "" },
      { label: "Narasimhan et al. 2019 (Science) — “The formation of human populations in South and Central Asia.”", url: "" }
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
        Kush populations, shaped by long-term geographic isolation. In regional
        models, they are often described as having elevated steppe-related and
        Iran-related ancestry, consistent with older regional layers rather than
        recent foreign input.
      </p>
    `
  },
{
  id: "averagemulato_brazil",
  title: "Average Mulato Brazilian",
  macro: "Latin America",
  country: "Brazil",
  region: "North & Northeast / coastal Brazil",
  category: "Average face",
  img: "images/avg_mulato_brazil.jpeg", // make sure this filename matches exactly
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
  category: "Average face",
  img: "images/avg_afrobajan.jpeg",
  tags: ["Barbados", "Afro-Bajan", "Caribbean", "Average face"],
  sources: [
    {
      label: "Murray T. et al. (2010). African and non-African admixture components in African Americans and an African Caribbean population. Genet Epidemiol 34(6):561–568.",
      url: ""
    },
    {
      label: "Parra E.J. et al. (2008). Admixture and population stratification in African Caribbean populations. Ann Hum Genet 72(1):90–98.",
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
  category: "Average face",
  img: "images/avg_kazakh.jpeg", // make sure this exists
  tags: ["Kazakh", "Central Asia", "Eurasian", "Average face"],
  sources: [
    {
      label: "Bidzhanov, D. et al. – External nose anthropometry in ethnic Kazakhs (nasal index, bridge height).",
      url: ""
    },
    {
      label: "Abilev, S. et al. – Genome-wide structure of Kazakhs and Central Asian populations (East/West Eurasian mix).",
      url: ""
    },
    {
      label: "Ismagulov, O. – Anthropological studies of Kazakh craniofacial type (mixed ‘Mongoloid–Caucasoid’ pattern).",
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

      <img src="images/mississipid-map.jpg"
           alt="Mississipid distribution map"
           style="display:block;width:100%;margin-top:10px;border-radius:12px;">
    `
  },

  {
    id: "chesapeakid",
    title: "Chesapeakid (African American phenotype)",
    macro: "North America",
    country: "United States",
    region: "Chesapeake Bay region",
    category: "Phenotype",
    img: "images/chesapeakid.jpg.JPEG",  // make sure this filename matches your actual image
    tags: [
      "Chesapeakid",
      "African American",
      "Free people of color",
      "Chesapeake",
      "Mid-Atlantic",
      "Phenotype"
    ],
    sources: [
      { label: "Berlin, Ira. Slaves Without Masters: The Free Negro in the Antebellum South (1974).", url: "" },
      { label: "Encyclopedia Virginia – entries on mulatto classification and free Blacks (e.g. 1785 'mulatto' act; Free Blacks during the Civil War).", url: "" },
      { label: "Maryland State Archives – essays on 'mulatto slave' laws (1664, 1715) and mulatto statistics.", url: "" },
      { label: "Paul Heinegg – Free African Americans of Virginia, North Carolina, South Carolina, Maryland and Delaware.", url: "" },
      { label: "Bryc, K. et al. (2014). Genetic ancestry of African Americans, Latinos, and European Americans across the United States.", url: "" },
      { label: "Shriver, M. et al. (2003). Admixture and ancestry estimates in African Americans.", url: "" },
      { label: "Henry Louis Gates Jr., African American Lives (PBS, 2006) – DNA summaries of African American ancestry.", url: "" },
      { label: "Bodenhorn, Howard (2011). Research on color, manumission, and freedom in the antebellum South.", url: "" }
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
        parts of the Great Lakes region. A similar phenotypic pattern can also
        appear among mixed-race Louisiana Creoles and other long-mixed families
        in the United States.
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

      <img
        src="images/chesapeakid_map.jpg"
        alt="Approximate core range of the Chesapeakid phenotype in the Chesapeake Bay region"
        style="display:block;width:100%;margin-top:10px;border-radius:12px;"
      >
    `
  },

  {
    id: "averageyakut",
    title: "Average Yakut",
    macro: "North Asia",
    country: "Russia",
    region: "Sakha Republic (Yakutia)",
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
