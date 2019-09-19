function equal_cols(el, toAdd) {
    var h = 0;
    $(el).each(function(){
        $(this).css({'height':'auto'});
        if($(this).outerHeight() > h)
        {
            h = $(this).outerHeight();
        }
    });
    $(el).each(function(){
        $(this).css({'height':h + toAdd});
    });
}

function getBootstrapBreakpoint() {
    var w = $(document).innerWidth();
    return (w < 768) ? 'xs' : ((w < 992) ? 'sm' : ((w < 1200) ? 'md' : 'lg'));
}

function showBlogPosts() {
    $('#blog .row>div').css({'display': 'block'});
    $('#blog .read-more').css({'display': 'none'});
}

$(document).ready(function(){
    equal_cols('#blog .blog-preview .card', 60);

    var breakpoint = getBootstrapBreakpoint(),
        cols = 2;

    if (breakpoint === 'lg') {
        cols = 5;
    } else if (breakpoint === 'md') {
        cols = 5;
    } else if (breakpoint === 'sm') {
        cols = 4;
    }

    $('#blog .row>div:nth-child(-n+' + cols + ')').css({'display': 'block'});
    $('#blog .row>div:nth-child(n+' + cols + ')').css({'display': 'none'});
});