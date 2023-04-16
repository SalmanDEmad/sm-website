const likeButtons = document.querySelectorAll('.like-btn');
const dislikeButtons = document.querySelectorAll('.dislike-btn');

likeButtons.forEach((button) => {
  button.addEventListener('click', (event) => {
    event.preventDefault();
    console.log('Like button clicked');
    const postID = button.dataset.postid;
    console.log('Post ID:', postID);
    fetch('/like', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: postID }),
    })
      .then((response) => {
        console.log('Fetch executed for like');
        return response.json();
      })

      .then((data) => {
        const parentElement = event.target.parentElement;
        const postLikesDislikes = parentElement.querySelector('#post-likes-dislikes');
        const likesDislikes = data.likes - data.dislikes;
        postLikesDislikes.innerHTML = isNaN(likesDislikes) ? 0 : likesDislikes;
      })

      .catch((error) => {
        console.error(error);
      });
  });
});

dislikeButtons.forEach((button) => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      console.log('Dislike button clicked');
      const postID = button.dataset.postid;
      console.log('Post ID:', postID);
      fetch('/dislike', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ post_id: postID }),
      })
      .then((response) => {
        console.log('Fetch executed for like');
        return response.json();
      })

      .then((data) => {
        const parentElement = event.target.parentElement;
        const postLikesDislikes = parentElement.querySelector('#post-likes-dislikes');
        const likesDislikes = data.likes - data.dislikes;
        postLikesDislikes.innerHTML = isNaN(likesDislikes) ? 0 : likesDislikes;
      })
      
      .catch((error) => {
        console.error(error);
      });
    });
  });
  
