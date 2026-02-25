/**
* 设置cookie的值
* @param name  键
* @param value 值
* @param time  过期时间，单位：秒
*/
function setCookie(name, value, time) {
    var expires = '';
    if (typeof time == 'number' && time > 0) {
        var exp = new Date();
        exp.setTime(exp.getTime() + time * 1000);
        expires = ';expires=' + exp.toGMTString();
    }

    document.cookie = name + '=' + value + expires + ';path=/';
}

// 获取cookie的值
function getCookie(name) {
    var reg = new RegExp("(^| )" + name + "=([^;]*)(;|$)");
    var r = document.cookie.match(reg);
    if (r != null) return decodeURI(r[2]); return null;
}

// 删除cookie
function delCookie(name) {
    var exp = new Date();
    exp.setTime(exp.getTime() - 3600);
    var value = getCookie(name);
    if (value) {
        document.cookie = name + '=' + value + ';expires=' + exp.toGMTString() + ';path=/';
    }
}

// 获取地址栏参数
function getParameter(name, params_str) {
    var reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)", 'i');
    var search = params_str || location.search.substr(1);
    var r = search.match(reg);
    if (r != null) return decodeURI(r[2]); return null;
}

// 时间字符串转为Date YYYY-MM-DD HH:II:SS
function toDate(timeStr) {
    var timeStr = timeStr.replace(/-/g, '/');
    return new Date(timeStr);
}

function addZero(num, n) {
    n = n || 2;
    return (Array(n).join(0) + num).slice(-n);
}

// 获取日期 YYYY-MM-DD
function getDate(timestamp) {
    timestamp = timestamp || 0;
    var date = new Date();
    if (timestamp != 0) {
        date = new Date(date.getTime() - timestamp);
    }

    var year = date.getFullYear();
    var month = addZero(date.getMonth() + 1);
    var day = addZero(date.getDate());
    return year + "-" + month + "-" + day
}

// 生成uuid
function generate_uuid() {
    var d = new Date().getTime();
    if (window.performance && typeof window.performance.now === "function") {
        d += performance.now();
    }
    var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,
        function (c) {
            var r = (d + Math.random() * 16) % 16 | 0;
            d = Math.floor(d / 16);
            return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
        });
    return uuid;
}

// 设置页面标题
function set_title(title) {
    document.title = title;
}

// 生成链接
function generate_url(add_params) {
    if (!add_params) {
        return location.href;
    }

    var params = [];
    if (location.search) {
        var query_str = location.search.substr(1);
        var query_arr = query_str.split('&');
        for (var i = 0; i < query_arr.length; i++) {
            var index = query_arr[i].indexOf('=');
            if (index !== -1) {
                params[query_arr[i].substring(0, index)] = query_arr[i].substring(index + 1);
            }
        }
    }

    // 新参数
    for (key in add_params) {
        params[key] = add_params[key];
    }

    // 转为字符串
    var params_arr = [];
    for (key in params) {
        params_arr.push(key + '=' + params[key])
    }
    return location.pathname + '?' + params_arr.join('&');
}

// 下载文件
function download(data, filename) {
    if (!data) return false;

    var url = window.URL.createObjectURL(new Blob([data]));
    var link = document.createElement('a');
    link.style.display = 'none';
    link.href = url;
    link.setAttribute('download', filename);

    document.body.appendChild(link);
    link.click();

    // 移除标签并释放blob对象
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}

// // base64编码
// function btoa(str) {
//     return Base64.encode(str);
// }

// // base64解码
// function atob(str) {
//     return Base64.decode(str);
// }

// MD5加密
function md5(str) {
    if (!str) return '';
    return $.md5(str);
}

// 浏览器信息
function getBrowserInfo() {
    var info = {};
    if ('ActiveXObject' in window && !window.ActiveXObject) {
        info.name = 'ie';
        info.version = '11';
    } else {
        var userAgent = navigator.userAgent.toLowerCase();
        var pattern = /(msie|firefox|chrome|opera|version|safari|qq).*?([\d.]+)/;
        var ret = userAgent.match(pattern);
        if (!ret) {
            info.name = 'sb';
            info.version = '1.0'
        } else {
            info.name = ret[1].replace(/version/, "safari");
            info.version = ret[2];
            if (info.name === 'msie') info.name = 'ie';
        }
    }

    return info;
}


// 价格格式化【全局方法】
Vue.prototype.formatPriceHtml = function (price) {
    if (!price && price !== 0) {
        return '';
    }
    var price = (Number(price) || 0).toFixed(2);
    var price_list = price.split('.');
    var price_int = price_list[0];
    var price_decimal = price_list[1];
    return '<i class="price-symbol">$</i> ' +
        '<i class="price-int">' + price_int + '</i>' +
        '<i class="price-decimal">.' + price_decimal + '</i> ';
};

// 价格过滤器
Vue.filter('formatPrice', function (price) {
    if (!price && price !== 0) {
        return '    ';
    }
    var price = Number(price) || 0;
    return '$ ' + price.toFixed(2);
});

// 汇率过滤器
Vue.filter('formatRate', function (rate) {
    var rate = Number(rate);
    return rate ? rate.toFixed(6) : '';
});

// 全部转为大写
Vue.filter('uppercase', function (str) {
    var str = str || '';
    return str.toUpperCase();
});

// 给价格加上符号
Vue.filter('signed', function (price) {
    var price = Number(price) || 0;
    return price > 0 ? '+ ' + price.toFixed(2) : '- ' + (-price).toFixed(2);
});

// 格式化字符串
Vue.filter('format', function (str, params) {
    var str = str || '';
    return str.replace(/{(\w+)}/g, function (r1, r2) {
        return params[r2];
    })
});

function cartNum() {
    var bl_cart = unescape(getCookie('bl_cart'));
    
    var total = 0;
    if (getCookie('bl_cart')) {
        var cart = JSON.parse(bl_cart);
        var addBool = true
        for (let index = 0; index < cart.length; index++) {
            console.log(cart[index])
            total += cart[index].num;
        }
        $('.cart-num').text(total > 99 ? '99+' : total);
    }
}

function showWxQr() {
    $('#qr_code_box').css("display", "flex")
    setTimeout(function () {
        $('#qr_code_box').css("display", "none");
    }, 2000)
}

function IsMobile() {
    //获取浏览器navigator对象的userAgent属性（浏览器用于HTTP请求的用户代理头的值）
    var info = navigator.userAgent;
    //通过正则表达式的test方法判断是否包含“Mobile”字符串
    var isPhone = /mobile/i.test(info);
    //如果包含“Mobile”（是手机设备）则返回true
    if(isPhone){
        $('.fixed_right').css("display", "none");;
    }
    return isPhone;
}