//do not include in your production env
//for demo purpose Only

// setTimeout(function () {
//     $(".modal:not(.auto-off)").modal("show");
// },200);

// (function($) {
//     //For demo purpose adding positions to modal for preview

//     $(document).on("click","[data-modal-position]",function (e) {
//         e.preventDefault();
//         //removing previously added classes
//         $("#positionModal").removeAttr("class");
//         // adding back modal class and the selected position
//         $("#positionModal").addClass( "modal fade " + $(this).attr('data-modal-position'));
//         //making the modal visible
//         $("#positionModal").modal("show");

//     })
// })(window.jQuery);


// $(document).on("click",".open-frame",function (e) {
//     if(window.innerWidth > 780){
//         e.preventDefault();
//         $("#frame").attr("src",$(this).attr("href"));
//     }
// });
// $('a[href^="#license"]').on('click',function (e) {
//     e.preventDefault();
//     var target = this.hash;
//     $target = $(target);
//     $('html, body').stop().animate({
//         'scrollTop':  $target.offset().top //no need of parseInt here
//     }, 900, 'swing', function () {
//         window.location.hash = target;
//     });
// });
let activePage = `1`;
let visited = [`1`];
let pages = document.querySelector('.pages');
let screens = document.querySelector('.screens');
let products = document.querySelector('.products');
let nextBtn = document.querySelector('.next-button');
let nextBtnText = document.querySelector('.next-button').children[0];
let screenTwo = document.querySelector('.screen-2');
let screenThree= document.querySelector('.screen-3');
let screenFour = document.querySelector('.screen-4');
let screensContainer = document.querySelector('#screens');
let closeBtn = document.querySelector('.close-button');
let pagesList = ``;
let screenList = ``;
let productList = ``;
for (let index = 1; index <= data.length; index++) {
    if(index === 1) {
        pagesList += `<li class='active'>${index}</li>`
    } else {
        pagesList += `<li>${index}</li>`;
    }
}
function renderList(options) {
    let result = ``;
    if(options === `NA`) {
        result += `<textarea name="feedback" placeholder="Type your feedback here... "></textarea>`;
    } else {
        for (let index = 0; index < options.length; index++) {
            if (options[index].image) {
                result += `<li id='${index}'><img src=${options[index].image} /> ${options[index].text}</li>`;
            } else if(options[index].emoji) {
                result += `<li id='${index}'>${options[index].emoji} ${options[index].text}</li>`;
            } else {
                result += `<li id='${index}'>${options[index].text}</li>`;
            }
        }
    }
    return result;
}
screenList = `<div class="screen screen-${1}">
            <h3 class="heading">${data[0].question}</h3>
            <ul class="products">
                ${renderList(data[0].options)}
            </ul>
        </div>`;
pages.insertAdjacentHTML('afterbegin', pagesList);
// pages.addEventListener('click', (e) => {
//     activePage = e.target.innerText;
//     for (let visit = 0; visit <= visited.length; visit++) {
//         if (visited.includes(e.target.innerText)) {
//             e.target.classList.add('visited');
//         }
//     }
//     if (!e.target.className) {
//         e.target.classList.add('active');
//     } else if(e.target.innerText !== `1`){
//         e.target.classList.remove('active');
//     }
//     for (const screen of screens.children) {
//         if (screen.className.includes(e.target.innerText)) {
//             screen.classList.add('active');
//             screen.classList.remove('hide');
//         } else {
//             screen.classList.add('hide');
//             screen.classList.remove('active');
//         }
//     }
//     // push only unique value to visisted array
//     if (visited.indexOf(e.target.innerText) === -1) {
//         visited.push(e.target.innerText);
//         screenList = `<div class="screen screen-${Number(activePage)}">
//             <h3 class="heading">${data[Number(activePage) - 1].question}</h3>
//             <ul class="products">
//                 ${renderList(data[Number(activePage) - 1].options)}
//             </ul>
//         </div>`;
//         screens.insertAdjacentHTML('afterbegin', screenList);
//     }
//     console.log('screen 1', visited);
// });
let result = [];
let screenNum = 2;
let lastScreen =  document.querySelector('#thankYouModal');
nextBtn.addEventListener('click', () => {
    let currentElement = '';
    for (const screen of screens.children) {
        currentElement = screen.tagName === 'DIV' && screen.lastElementChild.childNodes;
        if (screen.className.includes(screenNum)) {
            screen.classList.add('active');
            screen.classList.remove('hide');
        } else {
            screen.remove();
            // screen.classList.add('hide');
            // screen.classList.remove('active');
        }
    }
    currentElement = currentElement.length > 3 ? Array.from(currentElement).filter(item => item.className).map(ele => ele.innerText.trim()) : [currentElement[1].value];
    result.push({[`screen${screenNum - 1}`]: currentElement.join(', ')});
    if (screenNum === data.length) {
        nextBtnText.innerText = "Submit"
    }
    if (screenNum > data.length) {
        lastScreen.style.display = 'block';
        screensContainer.style.display = 'none';
    }
    if (!pages.children[screenNum - 1].className) {
        pages.children[screenNum - 1].classList.add('active');
    } else if(pages.children[screenNum - 1].innerText !== `1`){
        pages.children[screenNum - 1].classList.remove('active');
    }
    // push only unique value to visisted array
    if (visited.indexOf(String(screenNum)) === -1) {
        visited.push(String(screenNum));
        screenList = `<div class="screen screen-${screenNum}">
                <h3 class="heading">${data[screenNum - 1].question}</h3>
                <ul class="products">
                    ${renderList(data[screenNum - 1].options)}
                </ul>
            </div>`;
        screens.insertAdjacentHTML('afterbegin', screenList);
        screenNum++;
    }
})
screens.insertAdjacentHTML('afterbegin', screenList);
screens.addEventListener('click', (e) => {
    if (e.target.tagName === "LI" && !e.target.className) {
        e.target.classList.add('active');
        activePage = e.target.innerText;
        // if (e.target.offsetParent.firstChild.className.includes('screen-1')) {
        //     if (screenOneValue.indexOf(String(e.target.innerText)) === -1) {
        //         screenOneValue.push(e.target.innerText.trim());
        //     }
        // }
        // console.log('if', screenOneValue);
    } else {
        e.target.classList.remove('active');
        // if (e.target.offsetParent.firstChild.className.includes('screen-1')) {
        //     screenOneValue.splice(screenOneValue.indexOf(e.target.innerText.trim()), 1);
        //     console.log('else after', screenOneValue);
        // }
    }
});
closeBtn.addEventListener('click', () => {
    console.log('final', result)
    document.querySelector('#thankYouModal').style.display = 'none';
    moengage.trackClick();
    moengage.trackEvent('MOE_RESPONSE_SUBMITTED', Object.assign({}, ...result),{},{},false,true);
    moengage.dismissMessage();
})