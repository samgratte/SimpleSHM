function RenderCharts(url,divid,title) {
    // red, blue, orange, green, pink, brown, purple, yellow, white, gray 
    colors = ['#F15854','#5DA5DA','#FAA43A','#60BD68','#F17CB0','#B2912F','#B276B2','#DECF3F','#FFFFFF','#4D4D4D']
    var source = new EventSource(url);
    source.onmessage = function f(event){
        values = JSON.parse(event.data);
        values_length = 0;
        for (key in values){
            values_length += 1
        }
        console.log(event.data);
        console.log(values_length);
        if (typeof f.donnees === 'undefined') {
            f.chart = new SmoothieChart({
                    grid: { strokeStyle:'rgb(125, 0, 0)', fillStyle:'rgb(60, 0, 0)',
                    lineWidth: 1, millisPerLine: 1000, verticalSections: 6, },
                    labels: { fillStyle:'rgb(255, 255, 0)' }});
            console.log(f.chart)
            f.donnees = {};
            cell = '<td><b style="color:%color%">%name%</b></td><td><input type="checkbox" value="1" id="'+divid+'_%index%" name="%name%" checked></td>';
            // Création de la table des données
            table = '<table style="background-color:gray">'+'<caption>'+title+'</caption>'+'<tr><td rowspan='+(values_length+1)+'><canvas id="c'+divid+'" width="700" height="300"></canvas></td>';
            i = 0;
            for (key in values) {
                table += '</tr><tr>'+cell.replace('%color%',colors[i]).replace('%name%', key).replace('%index%',key);
                i++;
            }
            table += '</tr></table>';
            document.getElementById(divid).innerHTML = table
            i = 0
            for (key in values) {
                f.donnees[key] = new TimeSeries();
                f.chart.addTimeSeries(f.donnees[key],{ strokeStyle: colors[i], lineWidth: 2});
                f.chart.streamTo(document.getElementById('c'+divid), 1000);
                i++;
            }
        }
        now = new Date().getTime();
        for (key in values) {
            if (document.getElementById(divid+'_'+key).checked){
                f.donnees[key].append(now, values[key]);
            }
        }
    }
};
