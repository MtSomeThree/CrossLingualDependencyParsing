#

# language distances with word ordering (from the near-of-far project)

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

VECS = {'ar': [0.5, 0.0, 0.0006021458287716225, 0.9942345683989839, 0.9757539917208752, 0.5, 0.5, 0.5, 0.5701754385964912, 0.12786885245901639, 0.996031746031746, 0.5, 0.5, 0.9625, 0.9296289175158623, 0.5, 0.9191265669227658, 0.7694743508549715, 0.0, 0.7308533916849015, 0.020378457059679767, 0.02464788732394366, 0.0, 0.0017260635597522592, 0.638755980861244, 0.2724715338245144, 0.0010351966873706005, 0.056835177983846845, 0.0020920502092050207, 0.0018888289260658392, 0.5, 0.9539748953974896, 0.0, 0.011235955056179775, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.14974761637689288, 0.2953906080934863, 0.4624125874125874, 0.5, 0.1957690928648261, 0.5, 0.0, 0.0006323110970597534, 0.11045130641330166, 0.0009935419771485345, 0.0, 0.002036659877800407], 'bg': [0.0, 0.0, 0.9686029974838639, 1.0, 1.0, 1.0, 0.9136842105263158, 0.9690721649484536, 0.8315363881401617, 0.7066805845511482, 0.8851224105461394, 0.8591397849462366, 0.9841101694915254, 1.0, 1.0, 1.0, 0.9978448275862069, 0.9993472584856397, 0.0, 0.8074534161490683, 0.08865248226950355, 0.5, 0.0, 0.01034928848641656, 0.8264642082429501, 0.6959532568708072, 0.043669250645994834, 0.36171381488602034, 0.9413946587537092, 0.14965986394557823, 0.614100185528757, 0.9502026635784597, 0.779317697228145, 0.7803921568627451, 0.0026954177897574125, 0.0, 0.0, 0.7030527289546716, 0.5, 0.3041825095057034, 0.5213505461767627, 0.5416968817984047, 0.5, 0.5661070304302204, 0.26701021089798643, 1.0, 0.0, 0.003992015968063872, 0.34707574304889743, 0.042476601871850254, 0.0, 0.0049833887043189366], 'ca': [0.0, 0.0, 0.21146138013216337, 0.9949270607238403, 0.9937973811164714, 0.9999359508102222, 0.8925619834710744, 0.5, 0.6573795180722891, 0.6321411983279145, 0.9704433497536946, 0.9716479621972829, 0.9937435595465921, 0.9955801104972376, 0.9944174757281553, 0.9994761655316919, 0.9866747425802543, 0.9975413937903875, 0.0, 0.8598130841121495, 0.14874551971326164, 0.0006157635467980296, 0.0, 0.012211737397184235, 0.9585326953748007, 0.7473977120478202, 0.02220089571337172, 0.25923476617855457, 0.9558541266794626, 0.5, 0.9125475285171103, 0.9801467414760466, 0.8868908868908869, 0.899264705882353, 0.002170374389582203, 0.0, 0.0, 0.8300751879699249, 0.03775241439859526, 0.21723730814639905, 0.47613960113960113, 0.5146020232868868, 0.5712121212121212, 0.602001404494382, 0.26635238656452564, 0.9997888959256913, 0.0, 0.0008195377806916899, 0.15217965653896962, 0.11557562076749435, 0.0, 0.04321728691476591], 'zh': [0.0, 0.5, 1.0, 0.9994089834515366, 1.0, 1.0, 0.9969788519637462, 0.5, 1.0, 0.9983836206896551, 0.9931972789115646, 1.0, 1.0, 0.5, 0.9856957087126138, 0.9936708860759493, 0.9794520547945206, 1.0, 0.0, 1.0, 0.5, 0.28205128205128205, 0.0, 0.9972952086553323, 0.9981916817359855, 0.9990886998784934, 0.024272906188497704, 0.8826170622193714, 0.996309963099631, 1.0, 0.5, 1.0, 0.16981132075471697, 0.9763779527559056, 0.9995107632093934, 0.0, 0.5, 1.0, 0.014218009478672985, 0.8370786516853933, 0.6386138613861386, 0.6425619834710744, 0.5939086294416244, 0.802710843373494, 0.5861155883030164, 0.5, 0.0, 1.0, 0.5, 0.1362962962962963, 0.0, 0.2046692607003891], 'hr': [0.0, 0.0, 0.9908398121776615, 0.999818922589407, 1.0, 0.9994591671173607, 0.9611470860314524, 0.9538461538461539, 0.8924050632911392, 0.871765601217656, 0.7980107115531752, 0.8698275862068966, 0.6794297352342159, 0.9935897435897436, 0.9949109414758269, 0.9612546125461254, 0.9891761876127481, 0.9974926870037609, 0.0, 0.6441666666666667, 0.26339004410838057, 0.002336448598130841, 0.0, 0.01632984482136413, 0.8220640569395018, 0.7208972845336482, 0.09442346145301045, 0.3245992070332701, 0.9591708542713567, 0.5, 0.7407407407407407, 0.9411764705882353, 0.7434827945776851, 0.6582914572864321, 0.015977443609022556, 0.0, 0.0, 0.7283236994219653, 0.21875, 0.2927689594356261, 0.3691275167785235, 0.5603015075376885, 0.5282051282051282, 0.6483155299917831, 0.3405889884763124, 0.9941860465116279, 0.0, 0.0, 0.3477157360406091, 0.006150061500615006, 0.0, 0.0023885350318471337], 'cs': [0.0, 0.0, 0.9296791645561435, 0.9998678006433702, 0.9989373007438895, 0.9998011796673073, 0.9296763576522216, 0.9554310764734535, 0.9040316847770895, 0.7015156388196511, 0.938251024518997, 0.7511225864391559, 0.8371404399323181, 0.9879717959352966, 0.9864108086939495, 0.9839673058786546, 0.9589082836373134, 0.9845948632107548, 0.0, 0.7231609046009878, 0.3592086089003475, 0.0010025062656641604, 0.0, 0.009652725497357613, 0.6003986048829099, 0.6020300626767985, 0.20639981993472634, 0.3778496551186626, 0.7264876746742032, 0.6857923497267759, 0.7008797653958945, 0.9040880503144654, 0.7563776806586036, 0.7465303140978816, 0.025818371310815293, 0.0, 0.0, 0.5698587127158555, 0.5, 0.3985938345051379, 0.4758118380458637, 0.5935210101428275, 0.45516470109800733, 0.4047406348639152, 0.3930989146245944, 0.9973077487884869, 0.0, 0.0016869095816464238, 0.417230376515635, 0.2078100022836264, 0.0, 0.02353326778105539], 'da': [0.0, 0.0, 0.9681093394077449, 0.9937888198757764, 0.9028871391076115, 1.0, 0.9186666666666666, 0.8776824034334764, 0.7767722473604827, 0.5610163824807757, 0.976, 0.9634615384615385, 0.9899167032003507, 0.946236559139785, 0.9638009049773756, 0.9937106918238994, 0.9552364864864865, 0.9994971083731455, 0.0, 0.9716981132075472, 0.2388888888888889, 0.5, 0.0, 0.20102269095557687, 0.9866666666666667, 0.8334200937011973, 0.01935483870967742, 0.19711689125665935, 0.9360675512665863, 0.15625, 0.5, 0.826523777628935, 0.16964285714285715, 0.2796934865900383, 0.32599724896836313, 0.0, 0.0, 0.6561643835616439, 0.034782608695652174, 0.1465798045602606, 0.22966507177033493, 0.2558724832214765, 0.5, 0.3025335320417288, 0.18546162583157552, 0.9982668977469671, 0.0, 0.006802721088435374, 0.05301204819277108, 0.4891566265060241, 0.0, 0.3178294573643411], 'nl': [0.0, 0.0, 0.9932309557486361, 0.9960360774401102, 0.9844357976653697, 0.9990915697674418, 0.9539274924471299, 0.8215102974828375, 0.9228571428571428, 0.6932436301173777, 0.6113099498926271, 0.7185588035350102, 0.9065498539841469, 1.0, 0.9985479186834463, 0.9961636828644501, 0.9954633830200907, 0.9998829268292683, 0.0, 0.9301919720767888, 0.5550387596899224, 0.0, 0.0, 0.021348314606741574, 0.9476082004555809, 0.7956503318740291, 0.5721323011963406, 0.5249643366619116, 0.9450026441036489, 0.9737609329446064, 0.5362318840579711, 0.8325915290739412, 0.7322834645669292, 0.6868932038834952, 0.06149651620720994, 0.0, 0.0, 0.6825255669186305, 0.5231958762886598, 0.5149413020277481, 0.37218045112781956, 0.5058523409363745, 0.44591439688715956, 0.6515848670756647, 0.24098172746274696, 1.0, 0.0, 0.14980194454447246, 0.28346456692913385, 0.05442176870748299, 0.0, 0.054699537750385205], 'en': [0.0, 0.0, 0.9825544377944735, 0.9994686033123726, 0.9665116279069768, 1.0, 0.9548651817116061, 0.9367720465890182, 0.7389473684210527, 0.6134958166606038, 0.9922762380736029, 0.9905660377358491, 0.9959570612017287, 0.9973958333333334, 0.9984447900466563, 1.0, 0.9989792446410344, 1.0, 0.0, 0.9820971867007673, 0.2398989898989899, 0.007194244604316547, 0.0, 0.06345291479820628, 0.9848101265822785, 0.8851288419745421, 0.006386993758165191, 0.10878517501715855, 0.8938547486033519, 0.9336655247586422, 0.0, 0.9969788519637462, 0.12890792291220557, 0.12421383647798742, 0.21603005635566688, 0.0, 0.0, 0.972952086553323, 0.0, 0.08018504240555127, 0.2918149466192171, 0.3747673985857834, 0.23247863247863249, 0.3643141153081511, 0.27039473684210524, 0.99966239027684, 0.0, 0.003816793893129771, 0.23264025107885444, 0.04438807863031072, 0.0, 0.000974184120798831], 'et': [0.0, 0.0, 0.995731360273193, 0.21528461689974393, 0.12307692307692308, 0.23529411764705882, 0.9696202531645569, 0.9545163356822549, 0.9071902090770015, 0.5815959741193386, 0.8688080495356038, 0.7201674808094906, 0.9715660542432196, 0.9982949701619779, 0.9992764109985528, 1.0, 0.9957161981258367, 0.9913586173787806, 0.0, 0.8495989304812834, 0.89484827099506, 0.0, 0.0, 0.8269363653495823, 0.5751492132392838, 0.6048283367962798, 0.3136094674556213, 0.3939045776138356, 0.8488300492610837, 0.9508081517919887, 0.5, 0.8127076411960132, 0.6630383341221012, 0.5795555555555556, 0.9121002012972489, 0.0, 0.0, 0.5525562372188139, 0.3433583959899749, 0.37291527685123416, 0.43484301194776326, 0.5308707685756866, 0.5476374903175832, 0.5818639798488665, 0.37689157913476945, 0.9970358393963891, 0.0, 0.008333333333333333, 0.38724954462659383, 0.022131147540983605, 0.0, 0.09783989834815757], 'fi': [0.0, 0.0, 0.9990698910443795, 0.15738081562320505, 0.04644808743169399, 0.08032128514056225, 0.9713563605728728, 0.9468531468531468, 0.9035824856258293, 0.52210455538746, 0.921285140562249, 0.7654075546719682, 0.998093422306959, 1.0, 1.0, 1.0, 0.9983072365636902, 0.5, 0.0, 0.9338461538461539, 0.7339901477832512, 0.0, 0.0, 0.7711490916908524, 0.6477079796264855, 0.8484621155288822, 0.2526621490803485, 0.3423876911387596, 0.7368627450980392, 0.8932714617169374, 0.5, 0.9598853868194842, 0.5553925165077036, 0.6573705179282868, 0.9009633911368016, 0.0, 0.0, 0.8778391651319828, 0.36054421768707484, 0.3888888888888889, 0.37344913151364767, 0.49337199668599835, 0.44296296296296295, 0.6465863453815262, 0.34562764456981665, 1.0, 0.0, 0.6461824953445066, 0.2896393817973669, 0.0014367816091954023, 0.0, 0.011898323418063819], 'fr': [0.0, 0.0, 0.2851729323308271, 0.9999162595952548, 1.0, 1.0, 0.9833690987124464, 0.9490909090909091, 0.8293718166383701, 0.571178900540197, 0.9977827050997783, 1.0, 0.9998536942209217, 1.0, 1.0, 1.0, 0.9996536196744025, 0.9999793426842116, 0.0, 0.9841269841269841, 0.10416666666666667, 0.008955223880597015, 0.0, 0.006101247732644424, 0.9988425925925926, 0.9615727002967359, 0.0017336656192436883, 0.12890878422213572, 0.9471474438132872, 0.5664488017429193, 0.9941434846266471, 0.9851358277806254, 0.9127906976744186, 0.6146067415730337, 0.0007950389569088886, 0.0, 0.0, 0.9627039627039627, 0.0, 0.0595088161209068, 0.30892212480660136, 0.3305896186796573, 0.44523326572008115, 0.4895120839033288, 0.21929451763705907, 0.9946808510638298, 0.0, 0.013770826249574975, 0.23036187113857018, 0.0891089108910891, 0.0, 0.0007846214201647705], 'de': [0.0, 0.0, 0.9974449847523283, 0.9929879871718215, 0.9887514060742407, 0.997215777262181, 0.9771573604060914, 0.9261992619926199, 0.8826682549136391, 0.6530955585464334, 0.732409381663113, 0.8159917990773962, 0.6563989732306564, 0.9661654135338346, 0.9905832320777643, 0.9824175824175824, 0.9809384164222874, 0.9995657523340812, 0.0, 0.9461606354810238, 0.5, 0.006329113924050633, 0.0, 0.051970739163664154, 0.9145427286356822, 0.754248966467616, 0.44315915436777026, 0.6123564283067803, 0.9899274778404512, 0.5, 0.6373056994818653, 0.7368926445169963, 0.5093429776974081, 0.7576736672051696, 0.07871424955707416, 0.0, 0.0, 0.6849073256840247, 0.38716814159292035, 0.5281837160751566, 0.28042731781762686, 0.41285681132513347, 0.5311688311688312, 0.3867870449985669, 0.1260611777388492, 0.9960505529225908, 0.0, 0.020182291666666668, 0.3102310231023102, 0.21108179419525067, 0.0, 0.19635627530364372], 'he': [0.0, 0.0, 0.0, 0.999056974459725, 0.999485728979172, 1.0, 0.479646017699115, 0.5, 0.5, 0.636226034308779, 0.5, 0.5, 0.5, 0.996969696969697, 0.9929577464788732, 1.0, 0.9975339087546239, 1.0, 0.0, 0.8778135048231511, 0.5, 0.005376344086021506, 0.0, 0.03787299158377965, 0.9205128205128205, 0.5995121951219512, 0.018937987374675083, 0.21214004557696292, 0.8856115107913669, 0.0065764023210831725, 0.11666666666666667, 0.9851936218678815, 0.06725146198830409, 0.28469241773962806, 0.009615384615384616, 0.0, 0.0, 0.6475315729047072, 0.0375, 0.21241050119331742, 0.32936507936507936, 0.2478141393954534, 0.587378640776699, 0.25203989120580234, 0.2045748255363143, 1.0, 0.0, 0.0, 0.2639593908629442, 0.011538461538461539, 0.0, 0.0023894862604540022], 'hi': [0.0, 0.5, 0.999790904338735, 0.0005730330640077932, 0.001488833746898263, 0.0005754843660080568, 0.5, 0.5, 0.5, 0.9976717112922002, 0.0, 0.0, 0.0, 0.5, 0.9994295493439818, 0.9966442953020134, 0.9989195029713668, 1.0, 0.0, 0.9809069212410502, 0.5, 0.5, 0.0, 0.9880068532267275, 0.9969325153374233, 0.9967782602605407, 0.9519756838905775, 0.9979156184863077, 0.993279258400927, 0.9970760233918129, 0.5, 0.9996636394214599, 0.984304932735426, 0.99903784477229, 0.9902942068547164, 0.0, 0.5, 0.9987290828214361, 0.9868421052631579, 0.9980936242321542, 0.22882427307206069, 0.416351606805293, 0.5, 0.6948338005606728, 0.017116682738669238, 0.980866505388168, 0.0, 0.6179721287842384, 0.94034987094924, 0.5, 0.0, 0.5], 'id': [0.5, 0.5, 0.06296603148301574, 0.9833676268861454, 0.5, 0.9939420164430982, 0.9452887537993921, 0.5, 0.733502538071066, 0.9257592800899888, 0.5, 1.0, 0.5, 0.889763779527559, 0.9291479820627803, 0.956386292834891, 0.9618937644341802, 0.517490952955368, 0.0, 0.5, 0.5, 0.0, 0.0, 0.031007751937984496, 0.9314285714285714, 0.977533960292581, 0.0016901408450704226, 0.2174863387978142, 0.5046422719825232, 0.5, 0.5, 0.9991304347826087, 0.7116104868913857, 0.6132075471698113, 0.005714285714285714, 0.0, 0.0, 0.9880478087649402, 0.006745362563237774, 0.07734806629834254, 0.24896265560165975, 0.29595932566229594, 0.3150984682713348, 0.34635691657866946, 0.16698097034116235, 0.9869565217391304, 0.0, 0.0043454644215100485, 0.2261904761904762, 0.04365079365079365, 0.0, 0.07987220447284345], 'it': [0.0, 0.0, 0.3024896547045655, 1.0, 0.9993206521739131, 1.0, 0.9744707347447074, 0.9308176100628931, 0.866031746031746, 0.7110953562566465, 0.9786476868327402, 0.969047619047619, 0.9997301672962763, 0.9988207547169812, 0.9994202898550725, 1.0, 0.9987410826689047, 0.9982685937970491, 0.0, 0.7870967741935484, 0.14273204903677758, 0.5, 0.0, 0.016115240413076368, 0.9143389199255121, 0.724202089594962, 0.022573363431151242, 0.2089893346876587, 0.6923388731252533, 0.14130434782608695, 0.7049441786283892, 0.9577621341237496, 0.630716723549488, 0.6390086206896551, 0.010464058234758872, 0.0, 0.0, 0.6403361344537815, 0.010958904109589041, 0.2021201413427562, 0.2663755458515284, 0.2702960840496657, 0.3419354838709677, 0.3059643687064291, 0.13486772858045049, 1.0, 0.0, 0.007119741100323625, 0.30128956623681125, 0.0057859209257473485, 0.0, 0.0008271298593879239], 'ja': [0.0, 0.5, 1.0, 0.0, 0.0, 0.0, 1.0, 0.5, 1.0, 1.0, 0.5, 0.0, 0.0, 0.5, 0.5, 0.5, 0.5, 1.0, 0.0, 1.0, 1.0, 0.5, 0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 0.5, 1.0, 1.0, 0.5, 0.5, 1.0, 1.0, 1.0, 0.041237113402061855, 0.13142239048134127, 0.09945750452079566, 0.27756653992395436, 0.006300403225806451, 0.0, 0.0, 1.0, 1.0, 1.0, 0.5, 0.5], 'ko': [0.0, 0.5, 0.9960977613472992, 0.00145985401459854, 0.5, 0.5, 1.0, 0.6555299539170507, 0.9787985865724381, 0.9993382491964454, 0.5, 0.5, 0.0008712066211703209, 1.0, 0.9552238805970149, 0.5, 0.9996589358799455, 0.9961389961389961, 0.0, 1.0, 0.5, 0.16666666666666666, 0.0, 0.9969465648854962, 0.9922958397534669, 1.0, 0.9998667732480682, 0.5, 0.9589312221672439, 1.0, 0.5, 1.0, 1.0, 0.5, 1.0, 0.0, 0.0, 1.0, 1.0, 0.5, 0.025373134328358207, 0.17572952821699447, 0.19797979797979798, 0.36004331348132107, 0.01505821764442454, 0.5, 0.0, 0.9996917148362235, 0.9928892215568862, 0.9983349983349983, 0.0, 0.5], 'la': [0.0, 0.0, 0.5491403643828586, 1.0, 0.9340873634945398, 0.9981549815498155, 0.7502726281352236, 0.6484018264840182, 0.8972712680577849, 0.8801433337452119, 0.3075153374233129, 0.4512291831879461, 0.16589861751152074, 0.17131062951496387, 0.09839972761321075, 0.04656319290465632, 0.4124894987398488, 0.7940503432494279, 0.0, 0.47474747474747475, 0.46503496503496505, 0.02142857142857143, 0.0, 0.23707186030893218, 0.7697160883280757, 0.6350791258477769, 0.5291850220264317, 0.5544226044226044, 0.7223756906077348, 0.5, 0.38647089669638174, 0.9547151032595173, 0.633692173407041, 0.5876068376068376, 0.25307125307125306, 0.0, 0.0, 0.6312419974391805, 0.43614457831325304, 0.48255813953488375, 0.5, 0.5, 0.5, 0.5, 0.5, 0.9995822890559732, 0.0, 0.13640552995391705, 0.6037678051769031, 0.2799831081081081, 0.0, 0.4081858407079646], 'lv': [0.0, 0.0, 0.9978199937714107, 0.9905956112852664, 0.9913978494623656, 1.0, 0.9771573604060914, 0.981651376146789, 0.9800796812749004, 0.8170844939647168, 0.9106753812636166, 0.9281045751633987, 0.9977678571428571, 1.0, 1.0, 1.0, 0.9987163029525032, 0.9874248223072717, 0.0, 0.767175572519084, 0.6772151898734177, 0.5, 0.0, 0.8909607529746049, 0.9361702127659575, 0.5866797257590598, 0.17492260061919504, 0.4680502457673403, 0.990530303030303, 0.5, 0.6175710594315246, 0.9791304347826087, 0.7937743190661478, 0.8347978910369068, 0.9536817102137767, 0.0, 0.0, 0.7789473684210526, 0.5, 0.541501976284585, 0.5572005383580081, 0.5798845043310876, 0.5978835978835979, 0.5867237687366167, 0.4470292360892801, 1.0, 0.0, 0.003386004514672686, 0.42479908151549944, 0.06157354618015964, 0.0, 0.023923444976076555], 'no': [0.0, 0.0, 0.9581739015701279, 0.9970720485203388, 0.9336545589325427, 0.9991452991452991, 0.9095324833029751, 0.5, 0.8023980815347722, 0.6113055181695828, 0.9721559268098647, 0.9919632606199771, 0.9998424452497243, 1.0, 1.0, 1.0, 0.9995311034698343, 0.9972951312362252, 0.0, 0.9613466334164589, 0.20241437394722067, 0.0, 0.0, 0.17604555752862655, 0.9919935948759008, 0.7719852148467581, 0.012539184952978056, 0.17776143883264522, 0.9980175587652224, 0.5944218477629285, 0.2536912751677852, 0.8614061709661103, 0.22026641294005708, 0.1762917933130699, 0.22606803797468356, 0.0, 0.0, 0.6698799563477629, 0.0025412960609911056, 0.11950175165434021, 0.11072614407391367, 0.11594789222428999, 0.2890932982917214, 0.21894794822362984, 0.0820980235042735, 0.9983409999245909, 0.0, 0.000987004441519987, 0.1984126984126984, 0.006808169803764518, 0.0, 0.003157894736842105], 'pl': [0.0, 0.0, 0.6795947270944548, 0.9965809043507993, 1.0, 1.0, 0.8652482269503546, 0.8166089965397924, 0.5, 0.6967843756164924, 0.8877419354838709, 0.7049924357034796, 0.20185780635941408, 1.0, 1.0, 1.0, 1.0, 0.9584522676815731, 0.0, 0.8393632416787264, 0.19703977798334876, 0.5, 0.0, 0.010696974761825172, 0.47648902821316613, 0.6264439805149618, 0.14066666666666666, 0.30929360694554064, 0.9747596153846154, 0.8709175738724728, 0.35645933014354064, 0.8385744234800838, 0.4925373134328358, 0.4303253529772867, 0.005672609400324149, 0.0, 0.0, 0.8470661672908864, 0.19402985074626866, 0.3013530135301353, 0.3357817418677859, 0.45454545454545453, 0.5, 0.467680608365019, 0.24954559224477432, 0.9971988795518207, 0.0, 0.0, 0.34112646121147716, 0.00827966881324747, 0.0, 0.020699172033118676], 'pt': [0.0, 0.0, 0.3030022560305432, 0.9994964973730298, 1.0, 0.9998238713086361, 0.9558991981672395, 0.8863636363636364, 0.7289256198347107, 0.6983905579399141, 0.9751809720785936, 0.9271356783919598, 0.9991595461549236, 0.9572271386430679, 0.9758292620210851, 0.9776299879081015, 0.9780680137999014, 0.998464715881052, 0.0, 0.8077669902912621, 0.16936671575846834, 0.0009541984732824427, 0.0, 0.01586261143156791, 0.9584450402144772, 0.8542731921110299, 0.0045871559633027525, 0.18843062327052312, 0.9036271615352172, 0.5, 0.5, 0.967100633356791, 0.6671435383881735, 0.6630669546436285, 0.008635097493036212, 0.0, 0.0, 0.8841773685485825, 0.0035671819262782403, 0.11961057023643949, 0.4107296137339056, 0.46402570997573295, 0.5008625646923519, 0.5646727215784528, 0.26687007734336193, 0.9965706447187929, 0.0, 0.020189185373429338, 0.25774688676513174, 0.26671565025716387, 0.0, 0.004093567251461989], 'ro': [0.0, 0.0, 0.11806640625, 0.999029440310579, 0.9983606557377049, 1.0, 0.8959025470653378, 0.9518072289156626, 0.8643497757847534, 0.5327351279494849, 0.9720670391061452, 0.9445277361319341, 0.9998043052837573, 0.9642184557438794, 0.9870073624945864, 0.5, 0.9652917505030181, 0.8940948472412221, 0.0, 0.8181818181818182, 0.1310116086235489, 0.0, 0.0, 0.007945830166516963, 0.9141914191419142, 0.7790754257907543, 0.016703121893020482, 0.16787470877556304, 0.558300395256917, 0.17846153846153845, 0.9051724137931034, 0.9218828242363545, 0.8132820019249278, 0.6614950634696756, 0.0017857142857142857, 0.0, 0.0, 0.8519593613933236, 0.5, 0.1662269129287599, 0.5204525674499565, 0.5137411347517731, 0.4707835325365206, 0.5989010989010989, 0.2664130242434967, 1.0, 0.0, 0.0033651149747616375, 0.2632046160674656, 0.003682272488164124, 0.0, 0.12322274881516587], 'ru': [0.0, 0.0, 0.9852129977286422, 0.9974355321270836, 0.9997617913292044, 0.9989761092150171, 0.8861047835990888, 0.9510086455331412, 0.5004748338081672, 0.8050455501051156, 0.7317939609236235, 0.8013411567476949, 0.9700854700854701, 0.9997331198291967, 0.9974905897114178, 0.9941471571906354, 0.9984311782676906, 0.9714889123548046, 0.0, 0.7460916442048517, 0.45294353223868644, 0.004708097928436911, 0.0, 0.012339999014114592, 0.7643518518518518, 0.6524092783180688, 0.11611195158850227, 0.32135660078034556, 0.919118445337097, 0.4375804375804376, 0.6023516835916622, 0.9404867256637168, 0.6059595285746053, 0.6308411214953271, 0.007770103601381351, 0.0, 0.0, 0.7154451549434333, 0.5, 0.359504132231405, 0.45358269490761605, 0.420056544856106, 0.614226375908619, 0.45338906051244776, 0.4276681806259232, 0.9973596714257774, 0.0, 0.18447749433664926, 0.47976979420997556, 0.017635532331809273, 0.0, 0.04564372918978912], 'sk': [0.0, 0.0, 0.9653328050713154, 0.9997941539728283, 1.0, 1.0, 0.9658703071672355, 0.5, 0.5, 0.7294968986905582, 0.9382022471910112, 0.8296296296296296, 0.5564766839378238, 0.981042654028436, 0.9812286689419796, 0.5, 0.9963609898107715, 0.9937369519832986, 0.0, 0.7713004484304933, 0.3, 0.5, 0.0, 0.0059445178335535, 0.6158536585365854, 0.5583299222267704, 0.1349206349206349, 0.3485589994562262, 0.7976190476190477, 0.5, 0.6118143459915611, 0.8779443254817987, 0.6604381443298969, 0.4919210053859964, 0.014814814814814815, 0.0, 0.5, 0.660536398467433, 0.4343891402714932, 0.24378109452736318, 0.3978494623655914, 0.4356035064059339, 0.21333333333333335, 0.5852272727272727, 0.286475239284228, 1.0, 0.0, 0.0, 0.4179566563467492, 0.459, 0.0, 0.015706806282722512], 'sl': [0.0, 0.0, 0.9813336098724463, 0.999675148890092, 1.0, 1.0, 0.9617437722419929, 0.9298780487804879, 0.7748815165876777, 0.7664791901012373, 0.9106017191977077, 0.8893178893178894, 0.9314631278347052, 0.9981617647058824, 0.9960369881109643, 1.0, 0.9927045336112559, 0.9993449066491975, 0.0, 0.7700394218134035, 0.39864864864864863, 0.0, 0.0, 0.015848109210732778, 0.9, 0.6509186351706037, 0.2070275403608737, 0.4177799769091209, 0.8327402135231317, 0.5, 0.8892405063291139, 0.8838582677165354, 0.8745247148288974, 0.547486033519553, 0.01442672741078208, 0.0, 0.0, 0.7436974789915967, 0.38922155688622756, 0.44941176470588234, 0.46790890269151136, 0.5459263103269331, 0.5, 0.6124260355029586, 0.4034853823445386, 0.9991445680068435, 0.0, 0.0007027406886858749, 0.40893470790378006, 0.019384264538198404, 0.0, 0.019002375296912115], 'es': [0.0, 0.0, 0.25819471938709926, 0.9964580873671782, 0.9958677685950413, 0.999786514855008, 0.936735165088894, 0.5, 0.7623318385650224, 0.6624327555289898, 0.9747081712062257, 0.9911851126346719, 0.9923490835715487, 0.9847222222222223, 0.9910808590541016, 0.9895437262357415, 0.9849137931034483, 0.9982925380732194, 0.0, 0.8903508771929824, 0.09916201117318436, 0.003450920245398773, 0.0, 0.013095709570957096, 0.9364973262032086, 0.7546191978368635, 0.013583542713567839, 0.19660563074473475, 0.8798449612403101, 0.4184652278177458, 0.8667385610845787, 0.9680551205762605, 0.7714499113061338, 0.7405757368060315, 0.0028529626920263352, 0.0, 0.0, 0.8293730317778414, 0.02636916835699797, 0.12240501370936153, 0.4547677261613692, 0.48906794072394527, 0.5254604550379198, 0.5608829236739974, 0.3026903153421976, 0.9994041538985359, 0.0, 0.005629605099759914, 0.16788556678855668, 0.16803995006242198, 0.0, 0.02928094885100074], 'sv': [0.0, 0.0, 0.9975056123721626, 0.9960770936380693, 0.8842105263157894, 1.0, 0.9589442815249267, 0.9550561797752809, 0.9437340153452686, 0.5255544840887174, 0.9394904458598726, 0.8957219251336899, 0.999379652605459, 0.9884615384615385, 0.9661620658949243, 0.9759036144578314, 0.9794721407624634, 1.0, 0.0, 0.9299363057324841, 0.30526315789473685, 0.0, 0.0, 0.3026607538802661, 0.8947368421052632, 0.7694029850746269, 0.026395499783643445, 0.20505529225908373, 0.9136939010356732, 0.9219088937093276, 0.0, 0.861198738170347, 0.22146118721461186, 0.40641711229946526, 0.5, 0.0, 0.0, 0.7365269461077845, 0.5, 0.232, 0.23089430894308943, 0.3185011709601874, 0.5, 0.49777777777777776, 0.11465433300876339, 1.0, 0.0, 0.0, 0.2902338376891334, 0.01107011070110701, 0.0, 0.0], 'uk': [0.0, 0.0, 0.95618950585838, 0.9992773261065944, 1.0, 1.0, 0.8870967741935484, 0.9098039215686274, 0.9198606271777003, 0.7715669014084507, 0.9198113207547169, 0.78, 0.7194244604316546, 1.0, 1.0, 1.0, 1.0, 0.9798525798525799, 0.0, 0.7864077669902912, 0.15020576131687244, 0.0, 0.0, 0.005375139977603583, 0.7189189189189189, 0.6543671181690799, 0.1571259376233715, 0.3070429965708256, 0.967948717948718, 0.24468085106382978, 0.38095238095238093, 0.9457050243111832, 0.4962630792227205, 0.47401247401247404, 0.00823045267489712, 0.0, 0.0, 0.802675585284281, 0.2716049382716049, 0.37037037037037035, 0.5618971061093248, 0.6177056646740677, 0.7545454545454545, 0.5699658703071673, 0.44526053215077604, 1.0, 0.0, 0.0015552099533437014, 0.4146341463414634, 0.02857142857142857, 0.0, 0.036036036036036036]}

def get_distance(lang0, lang1):
    v0 = VECS[lang0]
    v1 = VECS[lang1]
    return np.average(np.abs(np.asarray(v0)-np.asarray(v1)))

# using the function get_distance, for example,
#  get_distance('de', 'en') will return a number indicating distance between German and English

LANGS = "ar bg ca zh hr cs da nl en et fi fr de he hi id it ja ko la lv no pl pt ro ru sk sl es sv uk".split()

#
def draw_heatmap(arr, xs, ys):
    fig, ax = plt.subplots()
    im = ax.imshow(arr)
    #
    ax.set_xticks(np.arange(len(xs)))
    ax.set_yticks(np.arange(len(ys)))
    ax.set_xticklabels(xs)
    ax.set_yticklabels(ys)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
         rotation_mode="anchor")
    for i in range(len(xs)):
        for j in range(len(ys)):
            text = ax.text(j, i, "%.1f"%(arr[i, j]*100),
                           ha="center", va="center", color="w")
    fig.tight_layout()
    plt.show()

def main():
    # (lang, lang) distance
    matrix = np.zeros((len(LANGS),len(LANGS)))
    for l1 in range(len(LANGS)):
        for l2 in range(len(LANGS)):
            matrix[l1][l2] = get_distance(LANGS[l1], LANGS[l2])
    print(matrix)
    draw_heatmap(matrix, LANGS, LANGS)
    avg = np.average(matrix, -1)
    print(np.average(matrix, -1))
    print(sorted([(LANGS[i], avg[i]) for i in range(len(LANGS))], key=lambda x: x[-1]))
    pass
    #
    print(sorted([(i, v) for i,v in enumerate(np.abs(np.array(VECS['en'])-np.array(VECS['de'])))], key=lambda x: x[-1], reverse=True))
    print(sorted([(i, v) for i,v in enumerate(np.abs(np.array(VECS['en'])-np.array(VECS['nl'])))], key=lambda x: x[-1], reverse=True))

if __name__ == '__main__':
    main()
