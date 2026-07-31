# توسعة الحالات v281

تضيف هذه الدفعة **50 صفحة حالة جديدة غير مكررة** فوق سجل v280. المحتوى الكامل مخزن بصورة مضغوطة قابلة لإعادة البناء حتميًا في `conditions-50-ar.json.zlib.b64`، ويقوم `scripts/publish_conditions_v281.py` بفكّه والتحقق منه وتوليد الصفحات وواجهة API وخريطة الموقع.

## حدود منهجية

- لا تشخيص آلي ولا جرعات ولا تعديل دواء أو حمية.
- لا ادعاء اعتماد أو مراجعة سريرية خارجية.
- لكل حالة مرجع مباشر من MedlinePlus أو NCBI/GeneReviews أو NINDS.
- كل صفحة تتجاوز 1000 كلمة وتحتوي 14 محورًا، وخطة للأهل ومقدم الخدمة وعلامات الخطر.
- الاختبارات تمنع التكرار مع المئة السابقة وتتحقق من 50 مسارًا فريدًا.

## الحالات

101. **متلازمة فيلان–ماكديرميد** — `phelan-mcdermid-syndrome`
102. **متلازمة بيت–هوبكنز** — `pitt-hopkins-syndrome`
103. **متلازمة موات–ويلسون** — `mowat-wilson-syndrome`
104. **المتلازمة المرتبطة بجين SATB2** — `satb2-associated-syndrome`
105. **متلازمة كليفسترا** — `kleefstra-syndrome`
106. **متلازمة كوفن–سيريس** — `coffin-siris-syndrome`
107. **متلازمة كوفن–لوري** — `coffin-lowry-syndrome`
108. **متلازمة نيكولايدس–بارايتسر** — `nicolaides-baraitser-syndrome`
109. **متلازمة فيدمان–شتاينر** — `wiedemann-steiner-syndrome`
110. **متلازمة ADNP (هلسـمورتل–فان دير آ)** — `adnp-syndrome`
111. **متلازمة DYRK1A** — `dyrk1a-syndrome`
112. **المتلازمة المرتبطة بجين MED13L** — `med13l-syndrome`
113. **متلازمة KBG** — `kbg-syndrome`
114. **متلازمة كولن–دي فريس** — `koolen-de-vries-syndrome`
115. **متلازمة كريستيانسون** — `christianson-syndrome`
116. **متلازمة FOXG1** — `foxg1-syndrome`
117. **الاضطراب النمائي العصبي المرتبط بجين DDX3X** — `ddx3x-related-neurodevelopmental-disorder`
118. **الاضطراب النمائي العصبي المرتبط بجين SETD5** — `setd5-related-neurodevelopmental-disorder`
119. **متلازمة وايت–ساتون** — `white-sutton-syndrome`
120. **متلازمة شيا–غيبس** — `xia-gibbs-syndrome`
121. **متلازمة بينبريدج–روبرز** — `bainbridge-ropers-syndrome`
122. **اضطراب نقص CDKL5** — `cdkl5-deficiency-disorder`
123. **متلازمة دريفت** — `dravet-syndrome`
124. **متلازمة لينوكس–غاستو** — `lennox-gastaut-syndrome`
125. **متلازمة لاندو–كليفنر** — `landau-kleffner-syndrome`
126. **الاضطراب المرتبط بجين STXBP1** — `stxbp1-related-disorder`
127. **الاضطراب المرتبط بجين SYNGAP1** — `syngap1-related-disorder`
128. **الاضطراب النمائي العصبي المرتبط بجين GRIN2B** — `grin2b-related-neurodevelopmental-disorder`
129. **الاضطرابات المرتبطة بجين SCN2A** — `scn2a-related-disorder`
130. **الاضطرابات المرتبطة بجين SCN8A** — `scn8a-related-disorder`
131. **الاضطراب النمائي العصبي المرتبط بجين HNRNPU** — `hnrnpu-related-neurodevelopmental-disorder`
132. **متلازمة PURA** — `pura-syndrome`
133. **الاضطرابات المرتبطة بجين CACNA1A** — `cacna1a-related-disorder`
134. **التنكس العصبي المرتبط ببروتين بيتا-بروبلر (WDR45/BPAN)** — `bpan-wdr45`
135. **الصرع المرتبط بجين KCNT1** — `kcnt1-related-epilepsy`
136. **الاعتلال النمائي الصرعي المرتبط بجين KCNQ2** — `kcnq2-developmental-epileptic-encephalopathy`
137. **داء مينكيس** — `menkes-disease`
138. **داء ويلسون** — `wilson-disease`
139. **داء بول شراب القيقب** — `maple-syrup-urine-disease`
140. **بيلة الهوموسيستين بسبب نقص CBS** — `homocystinuria-cbs-deficiency`
141. **داء عديدات السكاريد المخاطية النوع الأول** — `mucopolysaccharidosis-type-i`
142. **داء عديدات السكاريد المخاطية النوع الثاني (هانتر)** — `mucopolysaccharidosis-type-ii`
143. **داء عديدات السكاريد المخاطية النوع الثالث (سانفيليبو)** — `mucopolysaccharidosis-type-iii`
144. **داء عديدات السكاريد المخاطية النوع الرابع (موركيو)** — `mucopolysaccharidosis-type-iv`
145. **داء عديدات السكاريد المخاطية النوع السادس (ماروتو–لامي)** — `mucopolysaccharidosis-type-vi`
146. **داء غوشيه** — `gaucher-disease`
147. **داء فابري** — `fabry-disease`
148. **داء بومبي** — `pompe-disease`
149. **داء نيمان–بيك النوع C** — `niemann-pick-disease-type-c`
150. **الحثل الأبيض متبدل اللون** — `metachromatic-leukodystrophy`
