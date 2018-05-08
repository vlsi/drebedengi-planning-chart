function CCard(pay_date, free_days) {
    this.pay_date = pay_date;
    this.free_days = free_days;
}

// Кредитная карта с "датой выписки 8го числа и 21 льготным днём"
// ID нужно заменить на свой (это НЕ номер, который написан на самой карте, а это ID в системе ДребеДеньги)
var ccard_id = '111111111';

var ccards = {};
ccards[ccard_id] = new CCard(8, 21);
var place_that_pays_credit_debts = "2222222"; // В конце льготного периода будет погашена кредитная карта

var plan = document.getElementById('plan');

function isVisible(place_id) {
    var place = places[place_id];
    if (place === undefined || place.is_debt || place.is_hidden
        || ccards.hasOwnProperty(place_id)
    ) {
        return false;
    }
    return true;
}

function placeName(place_id) {
    var place = places[place_id];
    if (place === undefined) {
        return ''
    }
    return place.name;
}
function categoryName(category_id) {
    var category = categories[category_id];
    if (category === undefined) {
        return ''
    }
    return category.name;
}

var jsOffset = new Date().getTimezoneOffset();

function jsDate(date) {
    return new Date(date * 1000 + jsOffset);
}

function numWithSign(val) {
    if (val < 0) {
        return (val / 100 / 1000).toFixed(0);
    }
    return '+' + (val / 100 / 1000).toFixed(0);
}

function debitCreditText(debit, credit) {
    var shortText = '';
    if (credit < 0) {
        shortText = numWithSign(credit);
    }
    if (debit > 0) {
        if (shortText != '') {
            shortText += ' ';
        }
        shortText += numWithSign(debit);
    }
    return shortText;
}

function prepareData() {
    var total = 0;
    for (var place_id in balance) {
        if (!balance.hasOwnProperty(place_id)) {
            continue;
        }
        if (!isVisible(place_id)) {
            continue;
        }
        if (ccards[place_id]) {
            continue;
        }
        total += balance[place_id];
    }
    var i;
    var ignoreCategoryNames = {};
    var ignoreCategoryIds = {};
    for (i = 0; i < ignore_outdated.length; i++) {
        ignoreCategoryNames[ignore_outdated[i]] = true;
    }
    var catByName = {};
    for (var category_id in categories) {
        if (!categories.hasOwnProperty(category_id)) {
            continue;
        }
        var category = categories[category_id];
        if (ignoreCategoryNames[category.name]) {
            ignoreCategoryIds[category_id] = true;
        }
        catByName[category.name] = category;
    }

    var data = [];
    var nowDate = new Date();
    var tzOffset = nowDate.getTimezoneOffset()*60*1000;
    var now = (nowDate.getTime() - tzOffset) / 1000;

    trans.sort(function(a, b) {
        return a.date < b.date ? -1 : (a.date > b.date ? 1 : 0)
    });
    var prevDate = trans[0].date;
    var annotations = [];
    var re_planned = /(Просрочено! )?([^.]+)\.\s*(.*)/;
    var re_spaces = /\s\s+/;
    var ann = [];
    var shortText;
    for (i = 0; i < trans.length; i++) {
        var t = trans[i];
        if (t.is_planned && t.date < now && ignoreCategoryIds[t.category]) {
            t.ignore = true;
            continue;
        }

        if (t.comment) {
            t.comment = t.comment.replace(re_spaces, ' ');
            t.comment = t.comment.replace(/ {\d+;\d+} auto/g, '');
            // t.comment = t.comment.replace(/\s+Разово/g, '');
            t.comment = t.comment.replace(/Разово.\s+/g, '');
        }
        if (t.is_planned && t.comment) {
            var m = re_planned.exec(t.comment);
            if (m) {
                if (m[1]) {
                    t.comment = m[1] + m[3] + ' ' + m[2]
                } else {
                    t.comment = m[3] + ' ' + m[2];
                }
            }
        }

        if (ccards[t.from]) {
            continue;
        }

        if (prevDate != t.date) {
            var date = jsDate(prevDate);
            var d;
            if (t.date < now) {
                d = [date, total / 100 / 1000, NaN, total / 100 / 1000]
            } else {
                d = [date, NaN, total / 100 / 1000, total / 100 / 1000]
            }
            prevDate = t.date;
            if (ann.length > 0) {
                var transfer = 0;
                var debit = 0;
                var credit = 0;
                var txt = [];
                for (var j = 0; j < ann.length; j++) {
                    var amount = ann[j].amount;
                    if (amount > 0) {
                        debit += amount;
                    } else {
                        credit += amount;
                    }
                    txt.push(ann[j].text);
                }
                shortText = debitCreditText(debit, credit);
                // shortText = (debit / 100 / 1000).toFixed(0);
                annotations.push({
                    series: isNaN(d[1]) ? 'План' : 'Факт',
                    x: date.getTime(),
                    text: txt.join('\n'),
                    debit: debit,
                    credit: credit,
                    details: ann,
                    width: 23 + (shortText.length - 3) * 7,
                    shortText: shortText,
                    tickHeight: debit+credit > 0 ? 20 : -30,
                    tickWidth: -1, tickColor: 'white'
                });
                ann = [];
            }
            data.push(d);
        }

        // var txt = placeName(t.from) + ' => ' + placeName(t.to) + ' ' + t.amount / 100000;
        var diff = total;
        if (isVisible(t.from)) {
            total += t.amount;
        }
        if (isVisible(t.to)) {
            total -= t.amount;
        }
        diff = total - diff;
        // Amount
        if (Math.abs(t.amount)>1000000 // Отображать маркеры для сумм более 10т.р.
            // Перемещение денег между счетами, попадающими на график не должно отражаться маркером на графике
            && (isVisible(t.from) ^ isVisible(t.to))
            // && categoryName(t.category).indexOf('Работа') == -1
            // && categoryName(t.category).indexOf('Аванс') == -1
        ) {
            shortText = numWithSign(diff);
            var text = numWithSign(diff) + ' ₽, ' + formatDate(jsDate(t.date), nowDate) + ', ' + t.comment + ' ' + categoryName(t.category);
            text = text.replace(/ПланРемонта\s*/, '');

            ann.push({
                text: text,
                amount: diff,
                shortText: shortText
            });
        }
    }
    var min = Infinity;
    for(i=data.length-1; i>=0; i--){
        var val = data[i][3];
        if (min > val) {
            min = val;
        }
        data[i][3] = min;
    }
    return {data: data, annotations: annotations};
}

function calculateCreditCard(data, card_id) {
    var transIdx = 0;
    var tzOffset = new Date().getTimezoneOffset();
    var it = jsDate(trans[0].date);
    it.setHours(0,0,0,0);
    var maxTime = jsDate(trans[trans.length-1].date + 86400 * 55);
    var res = [];
    var new_trans = [];
    var current_loan = 0;
    var next_loan = balance[card_id];

    var ccard = ccards[card_id];
    var grace_pay_date = (ccard.pay_date + ccard.free_days - 1) % 31;
    var has_values = false;
    while(it < maxTime) {
        it.setDate(it.getDate() + 1);
        it.setHours(0, 0, 0, 0); // just in case
        var debit = 0;
        var credit = 0;
        for(; transIdx < trans.length && jsDate(trans[transIdx].date) < it; transIdx++) {
            var t = trans[transIdx];
            if (t.ignore) {
                continue;
            }
            if (t.from === card_id) {
                credit += t.amount;
                has_values = true;
            } else if (t.to === card_id) {
                debit += t.amount;
                has_values = true;
            }
        }
        if (current_loan < 0) {
            if (debit < current_loan) {
                debit -= current_loan;
                current_loan = 0;
            } else {
                current_loan -= debit;
                debit = 0;
            }
        }

        next_loan += credit - debit;

        // if (credit > debit) {
        //     loan -= credit - debit;
        // } else if (debit > credit) {
        //
        // }

        if (it.getDate() === ccard.pay_date) {
            current_loan = next_loan;
            next_loan = 0;
        }

        if (it.getDate() === grace_pay_date) {
            if (it < new Date()) {
              next_loan += current_loan
            } else {
            console.log([it, current_loan]);
            new_trans.push({"category": 0, "amount": current_loan, "from": place_that_pays_credit_debts, "is_planned": true, "comment": "возврат долга по кредитной карте"
                , "date": it.getTime()/1000-3600*4, "to": card_id.toString()});
            }
            current_loan = 0;
        }
        // if (res.length === 0 || res[res.length-1][1] !== current_loan || res[res.length-1][2] !== next_loan) {
            res.push([new Date(it), next_loan/100/1000, current_loan/100/1000]);
        // }
    }
    if (!has_values) {
        return [];
    }
    trans = trans.concat(new_trans);
    return res;
}

function lpad00(num) {
    if (num<10) {
        return '0' + num;
    }
    return num;
}

var month = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
function formatDate(d, now) {
    if (d.getUTCFullYear() != now.getUTCFullYear()) {
        return lpad00(d.getUTCDate()) + ' ' + month[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
    }
    return lpad00(d.getUTCDate()) + ' ' + month[d.getUTCMonth()];
}

var data = prepareData();
var ccdata = [];
if (trans.length > 0) {
    ccdata = calculateCreditCard(data, ccard_id);
    data = prepareData();
}

var graph_initialized = false;
var g = new Dygraph(plan, data.data, {
    // width: 480,
    // height: 320,
    labelsUTC: true,
    labels: ["Дата", "Факт", "План", "Свободно"],
    series: {
           "Факт": {
               stepPlot: true
           },
           "План": {
               stepPlot: true
           },
           "Свободно": {
               stepPlot: true
           },
    },
    drawCallback: function(g, is_initial) {
        if (is_initial) {
            graph_initialized = true;
            if (data.annotations.length > 0) {
                g.setAnnotations(data.annotations);
            }
        } else {
            var ap = g.layout_.annotated_points.concat();
            var html = [];
            ap.sort(function(u, v) {
                var a = u.annotation, b = v.annotation;
                if (a.credit !== b.credit) {
                    return a.credit - b.credit;
                }
                if (a.debit !== b.debit) {
                    return b.debit - a.debit;
                }
                return a.x - b.x;
            });
            var now = new Date();
            for(var i=0; i<ap.length; i++) {
                var ann = ap[i].annotation;
                html.push('<span style="width:5em; display:inline-block;">' + formatDate(new Date(ann.x), now) + '</span> ' + ann.text);
            }
            document.getElementById('top_annotations').innerHTML = html.join('<br>');
        }
    },
    annotationMouseOverHandler: function(ann, point, dg, event) {
        ann.div.style.width = 'auto';
        ann.div.style.height = 'auto';
        ann.div.style.zIndex = 100;
        ann.div.style.textAlign = 'left';
        ann.div.innerHTML = ann.text.replace(/\n/g, '<br>');
    },
    annotationMouseOutHandler: function(ann, point, dg, event) {
        ann.div.style.width = ann.width + 'px';
        ann.div.style.height = ann.height + 'px';
        ann.div.style.zIndex = 'initial';
        ann.div.style.textAlign = '';
        ann.div.innerHTML = ann.shortText;
    },
    underlayCallback: function(canvas, area, g) {

        canvas.fillStyle = "rgba(240, 240, 240, 1.0)";

        function highlight_period(x_start, x_end) {
            var canvas_left_x = g.toDomXCoord(x_start);
            var canvas_right_x = g.toDomXCoord(x_end);
            var canvas_width = canvas_right_x - canvas_left_x;
            canvas.fillRect(canvas_left_x, area.y, canvas_width, area.h);
        }

        var min_data_x = g.getValue(0,0);
        var max_data_x = g.getValue(g.numRows()-1,0);

        // get day of week
        var d = new Date(min_data_x);
        var dow = d.getUTCDay();

        var w = min_data_x - min_data_x % 86400000;
        // starting on Sunday is a special case
        if (dow === 0) {
            highlight_period(w,w+12*3600*1000);
        }
        // find first saturday
        while (dow != 6) {
            w += 24*3600*1000;
            d = new Date(w);
            dow = d.getUTCDay();
        }
        // shift back 1/2 day to center highlight around the point for the day
        //w -= 12*3600*1000;
        while (w < max_data_x) {
            var start_x_highlight = w;
            var end_x_highlight = w + 2*24*3600*1000;
            // make sure we don't try to plot outside the graph
            if (start_x_highlight < min_data_x) {
                start_x_highlight = min_data_x;
            }
            if (end_x_highlight > max_data_x) {
                end_x_highlight = max_data_x;
            }
            highlight_period(start_x_highlight,end_x_highlight);
            // calculate start of highlight for next Saturday
            w += 7*24*3600*1000;
        }
    },
});

if (graph_initialized) {
    g.setAnnotations(data.annotations);
}

if (ccdata.length == 0) {
    document.getElementById('credit').style.display = 'none';
} else {
    var ccg = new Dygraph(document.getElementById('credit'), ccdata, {
        labels: ["Дата", "next_loan", "current_loan"]
        , series: {
            "current_loan": {
                stepPlot: true
            },
            "next_loan": {
                stepPlot: true
            },
        }
        , stackedGraph: true
    });

    var sync = Dygraph.synchronize([g, ccg], {
        range: false
    });
}
g.updateOptions({}, false)
