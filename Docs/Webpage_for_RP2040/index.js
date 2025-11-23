var winWidth;
; (function (doc, win) {
    var htmlEle = doc.documentElement;
    var reload = "orientationchange" in window ? "orientationchange" : "resize";
    function setFontsize() {
        //每次通过屏幕转动或者重新设置宽高的时候获取屏幕宽度
        var clientWidth = htmlEle.clientWidth;
        if (!clientWidth) return;
        winWidth = clientWidth
        //设置html标签的fontsize大小
        if (clientWidth > 1280) {
            htmlEle.style.fontSize = 20 * (clientWidth / 384) + "px";
        } else if (clientWidth > 1080) {
            htmlEle.style.fontSize = 20 * (clientWidth / 256) + "px";
        } else {
            htmlEle.style.fontSize = 20 * (clientWidth / 216) + "px";
        }
    };
    win.addEventListener(reload, setFontsize, false);
    doc.addEventListener("DOMContentLoaded", setFontsize, false);
    var a = setTimeout(function () {
        clearTimeout(a);
    });
})(document, window);


$(function () {
    
    window.smsTimer = null;
    // 居中显示弹框
    function center(obj) {
        var screenWidth = $(window).width();
        screenHeight = $(window).height(); //当前浏览器窗口的 宽高
        var scrolltop = $(document).scrollTop();//获取当前窗口距离页面顶部高度
        var objLeft = (screenWidth - obj.width()) / 2;
        var objTop = (screenHeight - obj.height()) / 3 + scrolltop;
        obj.css({ left: objLeft + 'px', top: objTop + 'px', position: 'fixed' });
    }
    function ErrorTips(msg){
        $('.mask_login_tips').text(msg);
        setTimeout(function(){
            $('.mask_login_tips').text('');
        },3000)
    }
    
    function getWinWidth() {
        winWidth = $(window).width()
        if (winWidth <= 1080) {
            $('meta[name="viewport"]').attr('content', "width=1080px,user-scalable=no")
        }
    }
    getWinWidth()
    cartNum()
    showWxQr()
    IsMobile()
    $(window).resize(function () {
        getWinWidth()
    });

    $('.father li').mouseenter(function () {
        $(this).children('.child').stop().fadeIn().addClass('animated fadeInUp')
    }).mouseleave(function () {
        $(this).children('.child').stop().fadeOut().removeClass('animated fadeInUp')
    })

    $('.sort_ul li').mouseenter(function () {
        $(this).children('.sort_child1').stop().fadeIn().addClass('animated fadeIn')
        $(this).children('.sort_child2').stop().fadeIn().addClass('animated fadeIn')
    }).mouseleave(function () {
        $(this).children('.sort_child1').stop().fadeOut().removeClass('animated fadeIn')
        $(this).children('.sort_child2').stop().fadeOut().removeClass('animated fadeIn')
    })

    $('.product_detail_bottom .detail_bottom_left_nav li').click(function () {
        let _eq = $(this).index()
        $(this).addClass('active').siblings().removeClass('active')

        $('.detail_bottom_left_content').eq(_eq).show().siblings('.detail_bottom_left_content').hide()
    })

    $('.study_detail_bottom .detail_left_nav li').click(function () {
        let _eq = $(this).index()
        $(this).addClass('active').siblings().removeClass('active')

        $('.detail_left_content').eq(_eq).show().siblings('.detail_left_content').hide()
    })

    $('.study_article .study_article_nav .article_nav').click(function () {
        let _eq = $(this).index()
        $(this).addClass('active').siblings().removeClass('active')

        $('.study_article ul').eq(_eq).show().siblings('.study_article ul').hide()
    })

    // 顶部搜索
    $('#top_search_img').click(function () {
        let _val = $('#top_search').val()
        if (_val.length > 0) {
            $(this).parents('form').submit();
        } else {
            return layer.msg('请输入搜索内容');
        }
    })
    // 顶部搜索
    $('#top_search').bind('keyup', function (event) {
        if (event.keyCode == "13") {
            //回车执行查询
            $('#top_search_img').click();
        }
    });
    // 站内搜索
    $('#detail_search').bind('keyup', function (event) {
        if (event.keyCode == "13") {
            //回车执行查询
            let _val = $('#detail_search').val()
            if (_val.length > 0) {
                $('#detail_search_form').parents('form').submit();
            } else {
                return layer.msg('请输入搜索内容');
            }
        }
    });

    $('.product_nav_right .nav_right_sort').click(function () {
        var _type = $(this).index() + 1
        if ($(this).children('span').length != 0) {
            if ($(this).children('span').attr('attr-up') == 'false') {
                $(this).children('span').text('↑')
                $(this).children('span').attr('attr-up', 'true')
                _type = _type + 4
            } else {
                $(this).children('span').text('↓')
                $(this).children('span').attr('attr-up', 'false')
            }
        }

        $('#nav_type').val(_type)
        // return false
        $('#nav_type').parent('form').submit();
    })

    $('#advice_btn').click(function () {
        let data = $(this).siblings('form').serializeArray();
        if (data[0].value.length == 0) {
            return layer.msg('请输入手机号');
        }
        // if (!(/^1[3456789]\d{9}$/.test(data[0].value))) {
        //     return layer.msg("手机号码有误，请重填");
        // }
        if (data[1].value.length == 0) {
            return layer.msg('请输入您的姓名');
        }
        if (data[2].value.length == 0) {
            return layer.msg('请输入内容再提交');
        }
        $.post('/index/Advice/index', data, function (res) {
            if (res.status == 1) {
                layer.msg('感谢您的宝贵建议！');
                $('.complain_right form')[0].reset()
            } else {
                layer.msg(res.msg);
            }
        })
    })

    $('.slideDown').click(function () {
        $(this).hide()
        $('.close').fadeIn()
        $('.mobile_banner_nav').css('display', 'flex').stop().fadeIn().removeClass('fadeOut').addClass('animated fadeIn')
    })
    $('.close').click(function () {
        $(this).hide()
        $('.slideDown').fadeIn()
        $('.mobile_banner_nav').stop().fadeOut().removeClass('fadeIn').addClass('animated fadeOut')
    })


    layui.use('layer', function () {
        var layer = layui.layer;
    });

    // 支付信息切换
    $('.pay_item').click(function () {
        let _index = $(this).index()
        $('.pay_user').eq(_index).show().siblings('.pay_user').hide()
    })

    $('.mobile_sort_father > li > span').click(function () {
        if ($(this).attr('child-show') == 'true') {
            $('.mobile_sort_child').addClass('mobile_sort_child_hide')
            $('.mobile_sort_father > li > span').attr('child-show', 'false')
        } else {
            $('.mobile_sort_child').removeClass('mobile_sort_child_hide')
            $('.mobile_sort_father > li > span').attr('child-show', 'true')
        }
    })

    $('.fixed_right .service').mouseenter(function () {
        let _show = $(this).attr('attr-show')
        $('.fiexed_text').show().children('ul').hide()
        $('.fiexed_text').children('.' + _show).css('display', 'flex');
    })

    $('.fixed_right .qr_code, .fixed_right .qr_code a, .fixed_right .qr_code a span').mouseenter(function () {
        $('.fiexed_text').hide()
        $('#qr_code_box').css("display", "flex")
    });
    $('.fixed_right .qr_code, .fixed_right .qr_code a, .fixed_right .qr_code a span').mouseout(function () {
        $('#qr_code_box').css("display", "none")
    })
    $('.fixed_right .go_top').mouseenter(function () {
        $('.fiexed_text').hide()
    });
    $('.fixed_right').mouseleave(function () {
        $('.fiexed_text').hide()
    });

    $('.detail_left_nav li').click(function () {
        let _id = $(this).attr('attr-id')
        $('.detail_left_content[attr-id=' + _id + ']').show().siblings('.detail_left_content').hide()
    })

    $('.detail_bottom_left_nav li').click(function () {
        let _id = $(this).attr('attr-id')
        $('.detail_bottom_left_content[attr-id=' + _id + ']').show().siblings('.detail_bottom_left_content').hide()
    })
    

});
